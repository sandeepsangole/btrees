import bisect
from typing import Any, List, Optional, Tuple, Union, Dict, Generic, TypeVar, cast, NewType
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
        self.root_addr: Address = DISK.new()  # Remember, this is the ADDRESS of the root node
        # DO NOT RENAME THE ROOT MEMBER -- LEAVE IT AS self.root_addr
        DISK.write(self.root_addr, BTreeNode(self.root_addr, None, None, True))
        self.M = M  # M will fall in the range 2 to 99999
        self.L = L  # L will fall in the range 1 to 99999

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
        curr_node = self.get_root_node()
        leaf_to_insert = self.findLeafToInsert(key, curr_node)
        leaf_to_insert.insert_data(key, value)
        # Add to leaf and then validate if its full
        if self.isLeafFull(leaf_to_insert):
            # Insert into leaf and after that validate if root(M) is full
            updated_node = self.split_leaf(leaf_to_insert)
            while self.isMiddleNodeFull(updated_node):
                updated_node = self.split_middle(updated_node)
            updated_node.write_back()
        else:
            leaf_to_insert.write_back()

    """
        Methods to Support Insert funtionality
    """

    def split_leaf(self, node: BTreeNode):

        l_keys, l_data, left_children = self.leaf_left_split(node)
        r_keys, r_data, right_children = self.leaf_right_split(node)

        # Add new child to parent
        if node.parent_addr is None:
            new_root = BTreeNode(DISK.new(), None, None, True)
            parentAdd = new_root.my_addr
            self.insert_key(max(l_keys), new_root)
            new_root.is_leaf = False
            self.set_root_node(new_root)
        else:
            parent = node.get_parent()
            self.insert_key(max(l_keys), parent)
            parent.children_addrs.remove(max(l_keys))
            parentAdd = parent.my_addr

        # Create new Left node
        new_left_node = BTreeNode(DISK.new(), parentAdd, None, True)
        new_left_node.keys = new_left_node.keys + l_keys
        new_left_node.data = new_left_node.data + l_data
        new_left_node.children_addrs = new_left_node.children_addrs + left_children
        new_left_node.write_back()

        for child in new_left_node.children_addrs:
            cnode = get_node(child)
            cnode.parent_addr = new_left_node.my_addr
            cnode.write_back()

        # Create new Right node
        new_right_node = BTreeNode(DISK.new(), parentAdd, None, True)
        new_right_node.keys = new_right_node.keys + r_keys
        new_right_node.data = new_right_node.data + r_data
        new_right_node.children_addrs = new_right_node.children_addrs + right_children
        new_right_node.write_back()

        for child in new_left_node.children_addrs:
            cnode = get_node(child)
            cnode.parent_addr = new_left_node.my_addr
            cnode.write_back()

        # Returning so that we can check if this insert makes parent full
        if node.parent_addr is None:
            bisect.insort_right(new_root.children_addrs, new_left_node.my_addr)
            bisect.insort_right(new_root.children_addrs, new_right_node.my_addr)
            self.set_root_node(new_root)
            new_root.write_back()
            return new_root
        else:
            bisect.insort_right(parent.children_addrs, new_left_node.my_addr)
            bisect.insort_right(parent.children_addrs, new_right_node.my_addr)
            parent.write_back()
            return parent

    def split_middle(self, node: BTreeNode):
        l_keys, l_data, left_children = self.middle_left_split(node)
        r_keys, r_data, right_children = self.middle_right_split(node)

        # Add new child to parent
        if node.parent_addr is None:
            new_root = BTreeNode(DISK.new(), None, None, True)
            parentAdd = new_root.my_addr
            self.insert_key(max(l_keys), new_root)
            new_root.is_leaf = False
            self.set_root_node(new_root)
        else:
            parent = node.get_parent()
            self.insert_key(max(l_keys), parent)
            parent.children_addrs.remove(max(l_keys))
            parentAdd = parent.my_addr

        # Create new Left node
        new_left_node = BTreeNode(DISK.new(), parentAdd, None, True)
        new_left_node.keys = new_left_node.keys + l_keys
        new_left_node.data = new_left_node.data + l_data
        new_left_node.is_leaf = False
        new_left_node.children_addrs = new_left_node.children_addrs + left_children
        new_left_node.write_back()

        for child in new_left_node.children_addrs:
            cnode = get_node(child)
            cnode.parent_addr = new_left_node.my_addr
            cnode.write_back()

        # Create new Right node
        new_right_node = BTreeNode(DISK.new(), parentAdd, None, True)
        new_right_node.keys = new_right_node.keys + r_keys
        new_right_node.data = new_right_node.data + r_data
        new_left_node.is_leaf = False
        new_right_node.children_addrs = new_right_node.children_addrs + right_children
        new_right_node.write_back()


        for child in new_right_node.children_addrs:
            cnode = get_node(child)
            cnode.parent_addr = new_right_node.my_addr
            cnode.write_back()

        # Returning so that we can check if this insert makes parent full
        if node.parent_addr is None:
            bisect.insort_right(new_root.children_addrs, new_left_node.my_addr)
            bisect.insort_right(new_root.children_addrs, new_right_node.my_addr)
            self.set_root_node(new_root)
            new_root.write_back()
            return new_root
        else:
            bisect.insort_right(parent.children_addrs, new_left_node.my_addr)
            bisect.insort_right(parent.children_addrs, new_right_node.my_addr)
            parent.write_back()
            return parent

    def set_root_node(self, node: BTreeNode):
        self.root_addr = node.my_addr
        DISK.write(node.my_addr, node)

    def insert_key(self, key: KT, node:BTreeNode):
        idx = node.find_idx(key)
        node.keys.insert(idx, key)
        return node

    def leaf_left_split(self, node: BTreeNode):
        mid_index = self.leafMidIndex()
        keys = node.keys[:mid_index]
        data = node.data[:mid_index]
        children = node.children_addrs[:mid_index]
        return keys, data, children

    def leaf_right_split(self, node: BTreeNode):
        mid_index = self.leafMidIndex()
        keys = node.keys[mid_index:]
        data = node.data[mid_index:]
        children = node.children_addrs[mid_index:]
        return keys, data, children

    def middle_left_split(self, node: BTreeNode):
        mid_index = self.middleMidIndex()
        keys = node.keys[:mid_index]
        data = node.data[:mid_index]
        children = node.children_addrs[:mid_index]
        return keys, data, children

    def middle_right_split(self, node: BTreeNode):
        mid_index = self.middleMidIndex()
        keys = node.keys[mid_index:]
        data = node.data[mid_index:]
        children = node.children_addrs[mid_index:]
        return keys, data, children

    def leafMidIndex(self):
        return (self.L + 1) // 2

    def middleMidIndex(self):
        return (self.M + 1) // 2

    def findLeafToInsert(self, key, curr_node: BTreeNode) -> BTreeNode:
        if curr_node.is_leaf:
            return curr_node

        index = curr_node.find_idx(key)
        return self.findLeafToInsert(key, curr_node.get_child(index))

    def get_root_node(self):
        return get_node(self.root_addr)

    def isLeafNode(self, node: BTreeNode):
        return node.is_leaf

    def isLeafFull(self, node: BTreeNode):
        return len(node.keys) == self.L + 1

    def isMiddleNodeFull(self, node: BTreeNode):
        return len(node.keys) == self.M + 1

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
        curr_node = self.get_root_node()
        leaf_to_insert = self.findLeafToInsert(curr_node)
        return leaf_to_insert.find_data(key)

    def delete(self, key: KT) -> None:
        raise NotImplementedError("Karma method delete()")