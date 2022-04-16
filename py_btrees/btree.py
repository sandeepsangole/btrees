import bisect
import math
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
        if self.is_l_full(root) or self.is_m_full(root):
            new_address = DISK.new()
            #New node, with is_leaf = False, since the child will be the root
            new_root = BTreeNode(new_address, None, None, False)
            # Exchange addresses child-parent parent-child
            root.parent_addr = new_address
            new_root.children_addrs.insert(0, self.root_addr)
            #The new root is the new node we just created
            self.root_addr = new_address
            self.split_child(new_root, 0, root)
            self.insert_node_unfilled(new_root, key, value)
        else:
            self.insert_node_unfilled(root, key, value)
    
    def insert_node_unfilled(self, node: BTreeNode, key: KT, value:VT) -> None:
        if node.is_leaf and not self.is_l_full(node):
            node.insert_data(key, value)
            node.write_back()
            return
        else:
            idx = bisect.bisect_left(node.keys, key)
            # idx += 1
            # Read child from disk
            child_node = node.get_child(idx)
            # Let's check if there's space for M.
            if self.is_m_full(child_node) or self.is_l_full(child_node):
                self.split_child(node, key, child_node)
            return self.insert_node_unfilled(child_node, key, value)
    
    def split_child(self, node: BTreeNode, idx: int, child_node: BTreeNode) -> None:
        new_addrs = DISK.new()
        new_node = BTreeNode(new_addrs, None, None, child_node.is_leaf)
        
        # Copy the right side of the children to the new sibling node, in case this is not a leaf
        if not child_node.is_leaf:
            # Copy the right side of the keys to the new sibling node
            new_node.keys = child_node.keys[ceil(self.M//2):]
            new_node.children_addrs = child_node.children_addrs[(self.M//2)+1:]
            child_node.children_addrs = child_node.children_addrs[:(self.M//2)+1]
            # We can promote the key to the parent as well
            node.keys.insert(idx, child_node.keys[self.M//2])
            # Now that we have copied the keys to the new node, we can delete them from ourselves.
            child_node.keys = child_node.keys[:self.M//2]
        else:
            # Copy the right side of the keys to the new sibling node
            new_node.keys = child_node.keys[(self.L//2)+1:]
            new_node.data = child_node.data[(self.L//2)+1:]
            child_node.data = child_node.data[:(self.L//2)+1]
            # We can promote the key to the parent as well
            node.keys.insert(idx, child_node.keys[self.L//2])
            # Now that we have copied the keys to the new node, we can delete them from ourselves.
            child_node.keys = child_node.keys[:self.L//2]

        
        
        # Update parent and children pointers
        child_node.index_in_parent = idx
        new_node.index_in_parent = idx+1
        node.children_addrs.insert(idx+1, new_addrs)
        new_node.parent_addr = node.my_addr

        child_node.write_back()
        new_node.write_back()
        node.write_back()        
    
    def is_m_full(self, node: BTreeNode) -> bool:
        return len(node.keys) == self.M+1
    
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
