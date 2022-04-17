import bisect
from typing import Any, List, Optional, Tuple, Union, Dict, Generic, TypeVar, cast, NewType
from xmlrpc.client import Boolean

from py_btrees.disk import DISK, Address
from py_btrees.btree_node import BTreeNode, KT, VT, get_node

"""
----------------------- Starter code for your B-Tree -----------------------
Helpful Tips (You will need these):
1. Your tree should be composed of BTreeNode objects, where each node has:
    - the disk block address of its parent node
    - the disk block addresses of its children nodes (if non-leaf)
    - the data items inside (if leaf)
    - a flag indicating whether it is a leaf
------------- THE ONLY DATA STORED IN THE `BTree` OBJECT SHOULD BE THE `M` & `L` VALUES AND THE ADDRESS OF THE ROOT NODE -------------
-------------              THIS IS BECAUSE THE POINT IS TO STORE THE ENTIRE TREE ON DISK AT ALL TIMES                    -------------
2. Create helper methods:
    - get a node's parent with DISK.read(parent_address)
    - get a node's children with DISK.read(child_address)
    - write a node back to disk with DISK.write(self)
    - check the health of your tree (makes debugging a piece of cake)
        - go through the entire tree recursively and check that children point to their parents, etc.
        - now call this method after every insertion in your testing and you will find out where things are going wrong
3. Don't fall for these common bugs:
    - Forgetting to update a node's parent address when its parent splits
        - Remember that when a node splits, some of its children no longer have the same parent
    - Forgetting that the leaf and the root are edge cases
    - FORGETTING TO WRITE BACK TO THE DISK AFTER MODIFYING / CREATING A NODE
    - Forgetting to test odd / even M values
    - Forgetting to update the KEYS of a node who just gained a child
    - Forgetting to redistribute keys or children of a node who just split
    - Nesting nodes inside of each other instead of using disk addresses to reference them
        - This may seem to work but will fail our grader's stress tests
4. USE THE DEBUGGER
5. USE ASSERT STATEMENTS AS MUCH AS POSSIBLE
    - e.g. `assert node.parent != None or node == self.root` <- if this fails, something is very wrong
--------------------------- BEST OF LUCK ---------------------------
"""

# Complete both the find and insert methods to earn full credit
class BTree:
    def __init__(self, M: int, L: int):
        """
        Initialize a new BTree.
        You do not need to edit this method, nor should you.
        """
        self.root_addr: Address = DISK.new() # Remember, this is the ADDRESS of the root node
        # DO NOT RENAME THE ROOT MEMBER -- LEAVE IT AS self.root_addr
        DISK.write(self.root_addr, BTreeNode(self.root_addr, None, None, True))
        self.M = M # M will fall in the range 2 to 99999
        self.L = L # L will fall in the range 1 to 99999

    def insert(self, key: KT, value: VT) -> None:
        """
        Insert the key-value pair into your tree.
        It will probably be useful to have an internal
        _find_node() method that searches for the node
        that should be our parent (or finds the leaf
        if the key is already present).
        Overwrite old values if the key exists in the BTree.
        Make sure to write back all changes to the disk!
        """
        # Search to find the leaf into which X should be inserted
        root = get_node(self.root_addr)
        node_for_insert = self.find_rec(key,root,True)
        # Insert the key,value pair, overwriting if necessary
        node_for_insert.insert_data(key,value)
        # If the leaf has room, write leaf back to disk
        if self.hasEmptySpace(node_for_insert):
            node_for_insert.write_back()
        # otherwise, begin to split
        else:
            self.split(node_for_insert)

    def split(self,node):
        if node.my_addr == self.root_addr:
            self.split_root(node)
        elif node.is_leaf:
            self.split_leaf(node)
            
    def split_root(self,root):
        # Assuming that we are splitting the root(no parent)
        assert root.parent_addr == None
        print('splitting root')
        # Create a new root, which will not be a leaf
        new_root = BTreeNode(DISK.new(), None, None, False)
        # If the root is a leaf, we will make it a child of the new_root and then split it
        if root.is_leaf:
            print('root is leaf')
            root.parent_addr = new_root.my_addr
            root.index_in_parent = 0
            new_root.children_addrs.append(root.my_addr)
            self.root_addr = new_root.my_addr
            new_root.write_back()
            self.split_leaf(root)
        else:
            print('root is not leaf')
            root.parent_addr = new_root.my_addr
            root.index_in_parent = 0
            new_root.children_addrs.append(root.my_addr)
            self.root_addr = new_root.my_addr
            new_root.write_back()
            self.split_internal(root)
    
    def split_internal(self, node): 
        print('splitting internal')
        if node.parent_addr == None:
            self.split_root(node)
            return None
        parent_node = node.get_parent()
        # Find the median of the full node + inserted value and values before/after it
        # Bisecting left (values less than or equal to the median to the left, greater than to the right)
        if len(node.keys) > 0:
            mid_key = node.keys[self.get_mid_index(node) - 1]
        print('mid key is')
        print(mid_key)
        l_keys, l_data, left_children = self.left_children(node)
        print(l_keys)
        r_keys, r_data, right_children = self.right_children(node)
        print(r_keys)
        # Quick hack: Make l_keys not include the median
        l_keys = l_keys[:-1]
        # Create a new internal node and copy into it all the keys which appear after the median
        new_internal_node = BTreeNode(DISK.new(), node.parent_addr, None, False)
        new_internal_node.keys = new_internal_node.data + r_keys
        # Copy into its children_addrs all leaves that would go with it
        new_internal_node.children_addrs = new_internal_node.children_addrs + right_children
        self.update_index_in_parent(new_internal_node)
        # Clear the old internal node and replace it with left children data
        node.keys = []
        node.children_addrs = []
        node.children_addrs = node.children_addrs + left_children
        node.keys = node.keys + l_keys
        self.update_index_in_parent(node)
        # Move up the median at an appropriate position in the parent of the node
        idx = parent_node.find_idx(mid_key)
        parent_node.keys.insert(idx, mid_key)
        # Add additional child pointer from parent to the new node
        parent_node.children_addrs.insert(idx+1, new_internal_node.my_addr)
        # Update index_in_parents
        new_internal_node.index_in_parent = idx+1
        # Write everything back
        new_internal_node.write_back()
        node.write_back()
        parent_node.write_back()
        # If the new parent is now full, split again
        if len(parent_node.keys) > self.M - 1:
            self.split_internal(parent_node)
    
    def update_index_in_parent(self,internalnode):
        for index, child in enumerate(internalnode.children_addrs):
            childnode = get_node(child)
            if childnode.parent_addr != internalnode.my_addr:
                childnode.parent_addr = internalnode.my_addr
            childnode.index_in_parent = index
            childnode.write_back()
            

    def split_leaf(self, node):
        print('splitting leaf')
        # Assuming the parent of the full node is not full
        parent_node = node.get_parent()
        # Find the median of the full node + inserted value and values before/after it
        # Bisecting left (values less than or equal to the median to the left, greater than to the right)
        if len(node.keys) > 0:
            mid_key = node.keys[self.get_mid_index(node) - 1]
        print('mid key is')
        print(mid_key)
        l_keys, l_data, left_children = self.left_children(node)
        print(l_keys)
        r_keys, r_data, right_children = self.right_children(node)
        print(r_keys)
        # Create a new leaf node and copy into it all the keys which appear after the median
        new_leaf_node = BTreeNode(DISK.new(), node.parent_addr, None, True)
        new_leaf_node.keys = new_leaf_node.data + r_keys
        new_leaf_node.data = new_leaf_node.data + r_data
        # Clear the old leaf node and replace it with left children data
        node.keys = []
        node.data = []
        node.keys = node.keys + l_keys
        node.data = node.data + l_data
        # Move up the median at an appropriate position in the parent of the node
        idx = parent_node.find_idx(mid_key)
        parent_node.keys.insert(idx, mid_key)
        # Add additional child pointer from parent to the new node
        parent_node.children_addrs.insert(idx+1, new_leaf_node.my_addr)
        # Update index_in_parents
        new_leaf_node.index_in_parent = idx+1
        # Write everything back
        new_leaf_node.write_back()
        node.write_back()
        parent_node.write_back()
        # If the parent of the full node is now full
        if len(parent_node.keys) > self.M - 1:
            self.split_internal(parent_node)

    
    def hasEmptySpace(self, node: BTreeNode):
        if node.is_leaf:
            return len(node.keys) <= self.L
        else:
            return len(node.keys) <= self.M - 1
    
    def left_children(self, node) -> list:
        mid_index = self.get_mid_index(node)

        keys = node.keys[:mid_index]
        data = node.data[:mid_index]
        children = node.children_addrs[:mid_index]
        return keys, data, children

    def right_children(self, node) -> list:
        mid_index = self.get_mid_index(node)

        keys = node.keys[mid_index:]
        data = node.data[mid_index:]
        children = node.children_addrs[mid_index:]
        return keys, data, children

    def get_mid_index(self, node: BTreeNode) -> int:
        """Return middle index, if number of indexes is odd round it up."""
        if len(node.keys) % 2 == 0:
            return (len(node.keys) // 2)
        else:
            return (len(node.keys) // 2) + 1

    def find(self, key: KT) -> Optional[VT]:
        """
        Find a key and return the value associated with it.
        If it is not in the BTree, return None.
        This should be implemented with a logarithmic search
        in the node.keys array, not a linear search. Look at the
        BTreeNode.find_idx() method for an example of using
        the builtin bisect library to search for a number in
        a sorted array in logarithmic time.
            1. Get Root
            2. find if key is in root ( there will be multiple keys in root)
            3. Based on key value and closest matching key , go to left or right
            4. Repeat until you find key or reach leaf
            5. return value or None
        """
        root_node = get_node(self.root_addr)
        if root_node is None:
            return None

        return self.find_rec(key, root_node)

    def find_rec(self, key, bt_node, return_index_node=False):
        if bt_node.is_leaf:
            if return_index_node:
                print('returning node')
                return bt_node
            else:
                print('looking for data')
                return bt_node.find_data(key)
        else:
            #print('searching for index with key')
            #print(key)
            index = bt_node.find_idx(key)
            #print(index)
            return self.find_rec(key,bt_node.get_child(index),return_index_node)

    def printTree(self,printLeaves=True):
        q=[(get_node(self.root_addr),0)]
        i=0
        while len(q)!=0:
            n=q.pop()
            if n[1]!=i:
                print('--------------------------------')
            i=n[1]
            n=n[0]
            if printLeaves or not n.is_leaf:
                n.printNode()
            if n.children_addrs:
                for childAddr in n.children_addrs:
                    q.insert(0,(get_node(childAddr),i+1))
    
    def delete(self, key: KT) -> None:
        raise NotImplementedError("Karma method delete()")
