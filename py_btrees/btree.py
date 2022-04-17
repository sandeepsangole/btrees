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
        root = get_node(self.root_addr)
        if root.is_leaf and self.is_l_full(root):
            self.increase_height(root)

        leaf_node = self.find_leaf(key)
        self.insert_node_unfilled(leaf_node, key, value)
    
    def increase_height(self, node:BTreeNode) -> None:
        new_address = DISK.new()
        #New node, with is_leaf = False, since the child will be the root
        new_root = BTreeNode(new_address, None, None, False)
        # Exchange addresses child-parent parent-child
        node.parent_addr = new_address
        new_root.children_addrs.insert(0, self.root_addr)
        #The new root is the new node we just created
        self.root_addr = new_address
        self.split_child(new_root, 0, node)


    def find_leaf(self, key: KT) -> BTreeNode:
        temp = get_node(self.root_addr)
        while not temp.is_leaf:
            i = 0
            while i < len(temp.keys) and key > temp.keys[i]:
                i += 1
            temp = get_node(temp.children_addrs[i])
        return temp
    
    def insert_node_unfilled(self, node: BTreeNode, key: KT, value:VT) -> None:
        if not self.is_l_full(node) and node.is_leaf:
            node.insert_data(key, value)
            node.write_back()
            return
        else:
            parent = get_node(node.parent_addr)
            # Insert Left
            if self.insert_left(node, parent, key, value):
                return
            if self.insert_right(node, parent, key, value):
                return
            self.split_child(parent, node.index_in_parent, node)
            node.insert_data(key, value)
            node.write_back()
            if self.is_m_full(parent):
                grandparent_node = get_node(parent)
                self.split_child(grandparent_node, node.index_in_parent, parent)

    
    def insert_left(self, node: BTreeNode, parent_node:BTreeNode, key:KT, value:VT) -> bool:
        idx = node.index_in_parent
        if idx and idx-1 >= 0:
            left_child = get_node(parent_node.children_addrs[idx-1])
            if not self.is_l_full(left_child):
                key_idx = bisect.bisect_left(parent_node.keys, left_child.keys[-1])
                left_child.insert_data(node.keys.pop(0), node.data.pop(0))
                parent_node.keys.pop(key_idx)
                node.insert_data(key, value)
                parent_node.keys.insert(key_idx, left_child.keys[-1])
                node.write_back()
                parent_node.write_back()
            return True
        return False
    
    def insert_right(self, node: BTreeNode, parent_node:BTreeNode, key:KT, value:VT) -> bool:
        idx = node.index_in_parent
        if idx and idx+1 > 0 and idx+1<len(parent_node.children_addrs):
            right_child = get_node(parent_node.children_addrs[idx+1])
            if not self.is_l_full(right_child):
                key_idx = bisect.bisect_left(parent_node.keys, node.keys[-1])
                node.insert_data(key, value)
                right_child.insert_data(node.keys.pop(-1), node.data.pop(-1))
                parent_node.keys.pop(key_idx)
                parent_node.keys.insert(key_idx, node.keys[-1])
                node.write_back()
                parent_node.write_back()
            return True
        return False

    def split_child(self, parent_node: BTreeNode, idx: int, node: BTreeNode) -> None:
        if parent_node == None and node.my_addr == self.root_addr:
            self.increase_height(node)
            
        new_addrs = DISK.new()
        new_node = BTreeNode(new_addrs, None, None, node.is_leaf)
        
        # Copy the right side of the children to the new sibling node, in case this is not a leaf
        if not node.is_leaf:
            # Copy the right side of the keys to the new sibling node
            new_node.keys = node.keys[(self.M//2)+1:]
            new_node.children_addrs = node.children_addrs[(self.M//2)+1:]
            node.children_addrs = node.children_addrs[:(self.M//2)+1]
            # We can promote the key to the parent as well
            parent_node.keys.insert(idx, node.keys[self.M//2])
            # Now that we have copied the keys to the new node, we can delete them from ourselves.
            node.keys = node.keys[:(self.M//2)]
        else:
            # Copy the right side of the keys to the new sibling node
            new_node.keys = node.keys[(self.L//2)+1:]
            new_node.data = node.data[(self.L//2)+1:]
            node.data = node.data[:(self.L//2)+1]
            # We can promote the key to the parent as well
            parent_node.keys.insert(idx, node.keys[self.L//2])
            # Now that we have copied the keys to the new node, we can delete them from ourselves.
            node.keys = node.keys[:(self.L//2)+1]
        
        # Update parent and children pointers
        node.index_in_parent = idx
        new_node.index_in_parent = idx+1
        parent_node.children_addrs.insert(idx+1, new_addrs)
        new_node.parent_addr = parent_node.my_addr

        node.write_back()
        new_node.write_back()
        parent_node.write_back()

        if self.is_m_full(parent_node):
            grandparent_node = get_node(parent_node)
            return self.split_child(grandparent_node, parent_node.index_in_parent, parent_node)      
    
    def is_m_full(self, node: BTreeNode) -> bool:
        return len(node.children_addrs) > self.M
    
    def is_l_full(self, node: BTreeNode) -> bool:
        return len(node.data) == self.L

    def find(self, key: KT) -> Optional[VT]:
        """
        Find a key and return the value associated with it.
        If it is not in the BTree, return None.

        This should be implemented with a logarithmic search
        in the node.keys array, not a linear search. Look at the
        BTreeNode.find_idx() method for an example of using
        the builtin bisect library to search for a number in 
        a sorted array in logarithmic time.
        """
        temp = get_node(self.root_addr)
        if temp.keys:
            return self.find_helper(temp, key)
        return None

    def find_helper(self, node: BTreeNode, key: KT) -> Optional[VT]:
        #bisect right?
        idx = bisect.bisect_left(node.keys, key)
        if idx < len(node.keys) and node.keys[idx] == key and node.is_leaf:
            return node.data[idx]
        if node.is_leaf:
            return None
        child_node = node.get_child(idx)
        return self.find_helper(child_node, key)
    
    def delete(self, key: KT) -> None:
        raise NotImplementedError("Karma method delete()")
