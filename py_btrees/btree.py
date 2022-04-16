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

        """
            1. Find key to check if it exist
              1.1. If yes, replace else continue
            2. Find the leaf where this key can be inserted 
            3. If the leaf has room (fewer than L elements), insert X
                and write the leaf back to the disk
            4. 
        """
        root_node = get_node(self.root_addr)
        self.insert_util(key, value, root_node)

    def insert_util(self, key, value, node: BTreeNode):
        # root is none , create root and add key
        idx, node_to_insert = self.find_rec(key, node, True)
        node_to_insert.keys.insert(idx, key)
        node_to_insert.data.insert(idx, value)
        if self.hasEmptySpace(node_to_insert):
            DISK.write(node_to_insert.my_addr, node_to_insert)
        else:
            new_root = self.split_node(node_to_insert)
            if new_root.parent_addr is None:
                self.updatedIndexInParent(new_root)
                self.set_root_node(new_root)
                DISK.write(self.root_addr, get_node(self.root_addr))
            else:
                new_root.write_back()

    def hasEmptySpace(self, node: BTreeNode):
        if self.isLeafNode(node):
            return len(node.keys) <= self.L
        else:
            return len(node.keys) <= self.M - 1

    def isLeafNode(self, node: BTreeNode):
        return node.is_leaf

    def merge_up(self, parent_node, node, index):
        pivot = node.keys[0]
        parent_node.children_addrs.pop(index)
        parent_node.children_addrs = parent_node.children_addrs + node.children_addrs

        newindex = index
        for child in node.children_addrs:
            child_node = get_node(child)
            if not self.hasEmptySpace(parent_node):
                child_node.parent_addr = node.my_addr

            child_node.index_in_parent = newindex
            if len(child_node.keys) == len(child_node.children_addrs):
                child_node.keys.pop()

            newindex+=1
            if len(child_node.children_addrs) > 0:
                child_node.is_leaf = False

            child_node.write_back()

        for i, item in enumerate(parent_node.keys):
            if pivot < item:
                parent_node.keys = parent_node.keys[:i] + [pivot] + parent_node.keys[i:]
                break

            elif i + 1 == len(parent_node.keys):
                parent_node.keys += [pivot]
                break

        # index = 0
        # for child in parent_node.children_addrs:
        #     updated_child = get_node(child)
        #     updated_child.index_in_parent = index
        #     updated_child.parent_addr = parent_node.my_addr
        #     index +=1
        #     DISK.write(updated_child.my_addr, updated_child)

        # self.set_root_node(parent_node)

    def updatedIndexInParent(self,parent_node):
        index = 0
        for child in parent_node.children_addrs:
            updated_child = get_node(child)
            updated_child.index_in_parent = index
            updated_child.parent_addr = parent_node.my_addr
            if len(updated_child.keys) == len(updated_child.children_addrs):
                updated_child.keys.pop()
            index +=1
            if len(updated_child.children_addrs) > 0:
                updated_child.is_leaf = False

            updated_child.write_back()

    def updateIndexRec(self, parent_node):
        if parent_node and parent_node.children_addrs and len(parent_node.children_addrs) == 0:
            return

        index = 0
        queue = []
        queue.append([child for child in parent_node.children_addrs])

        while len(queue) > 0:
            node = queue.pop()
            updated_child = get_node(node)
            updated_child.index_in_parent = index
            updated_child.parent_addr = parent_node.my_addr
            index +=1
            if len(updated_child.children_addrs) > 0:
                updated_child.is_leaf = False
            updated_child.write_back()
            queue.append([child for child in node.children_addrs])


        # for child in parent_node.children_addrs:
        #     queue.append(child)
        #
        #     updated_child = get_node(child)
        #     updated_child.index_in_parent = index
        #     updated_child.parent_addr = parent_node.my_addr
        #     index +=1
        #     if len(updated_child.children_addrs) > 0:
        #         updated_child.is_leaf = False
        #     updated_child.write_back()
        #     return self.updateIndexRec(child)

    def split_node(self, node: BTreeNode) -> BTreeNode:

        while not self.hasEmptySpace(node):
            if self.is_it_root_node(node):
                node = self.split_node_util(node)
                self.updatedIndexInParent(node)
                self.set_root_node(node)
            else:
                par_add = node.parent_addr
                node = self.split_node_util(node)  # Split & Set node as the 'top' node.
                parent_node = get_node(par_add)
                idx = self.find_idx_util(node.keys[0], parent_node)

                # If sibling doesnt satisfy m/2 property then merge
                self.merge_up(parent_node, node, idx)
                node = parent_node
        return node

    def split_node_util(self, node: BTreeNode)->BTreeNode:

        l_keys, l_data, left_children = self.left_children(node)
        r_keys, r_data, right_children = self.right_children(node)
        # Move key up to the new root and set
        mid_key = self.get_mid_index(node)

        top_node = BTreeNode(DISK.new(), None, None, False)
        top_node.keys.append(l_keys[mid_key - 1])

        if node.parent_addr and self.hasEmptySpace(node.get_parent()):
            parentAdd = node.parent_addr
        else:
            parentAdd = top_node.my_addr

        new_left_node = BTreeNode(DISK.new(), parentAdd,None, True)
        new_left_node.keys = new_left_node.keys + l_keys
        new_left_node.data = new_left_node.data + l_data
        new_left_node.children_addrs = new_left_node.children_addrs + left_children
        new_left_node.write_back()

        for child in new_left_node.children_addrs:
            cnode = get_node(child)
            cnode.parent_addr = new_left_node.my_addr
            cnode.write_back()

        new_right_node = BTreeNode(DISK.new(), parentAdd,None, True)
        new_right_node.keys = new_right_node.keys + r_keys
        new_right_node.data = new_right_node.data + r_data
        new_right_node.children_addrs = new_right_node.children_addrs + right_children
        new_right_node.write_back()

        for child in new_right_node.children_addrs:
            cnode = get_node(child)
            cnode.parent_addr = new_right_node.my_addr
            cnode.write_back()

        top_node.children_addrs.append(new_left_node.my_addr)
        top_node.children_addrs.append(new_right_node.my_addr)
        return top_node

    def get_root_node(self):
        return get_node(self.root_addr)

    def set_root_node(self, node: BTreeNode):
        self.root_addr = node.my_addr
        DISK.write(node.my_addr, node)


    def add_key_to_node(self, key: int, node: BTreeNode):
        index = self.find_idx_to_insert(key)
        node.keys.insert(index, key)

    def is_it_root_node(self, node: BTreeNode) -> bool:
        return node.parent_addr is None

    def set_root(self, root: BTreeNode):
        self.root_addr = root

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
        """Return middle index, if number of indexes is odd round it down."""
        return len(node.keys) // 2

    def get_mid_key(self, node) -> int:
        """Return key at middle index."""
        return node.keys[self.get_mid_index()]

    # def set_parent(self, parent: BTreeNode):
    #     """Set parent"""
    #     self.parent = parent
    #
    # def get_parent(self):
    #     return self.parent
    #
    # def set_parent_for_children(self, parent: BTreeNode = None):
    #     """
    #     Set parent for all children of current node.
    #     Args:
    #         parent (BTreeNode): parent to set
    #     """
    #     if parent is None:
    #         parent = self
    #     for child in self.children:
    #         child.set_parent(parent)
    #
    # def number_of_keys(self) -> int:
    #     """Return number of keys in self.keys"""
    #     return len(self.keys)
    #
    # def number_of_children(self) -> int:
    #     """Return number of children in self.children"""
    #     return len(self.children)

    def find_idx_to_insert(self, key, node: BTreeNode = None) -> BTreeNode:
        if node is None:
            return node

        return self.find_rec(key, node, True)

    def is_it_full_node(self, node: BTreeNode) -> bool:
        if node is None:
            return False
        return len(node.keys) > self.maxKeysAllowed()

    def maxKeysAllowed(self):
        return self.M - 1

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
        root_node = self.get_root_node()
        if root_node is None:
            return None

        return self.find_rec(key, root_node)

    def find_idx_util(self, key: KT, node: BTreeNode) -> Optional[int]:
        """
        Finds the index in self.keys where `key`
        should go, if it were inserted into the keys list.

        Assumes the keys array is sorted. Works in logarithmic time.
        """
        # Get index of key
        return bisect.bisect_left(node.keys, key)

    def find_rec(self, key, bt_node, return_index_node=False):
        if bt_node.is_leaf:
            if return_index_node:
                idx = bt_node.find_idx(key)
                return idx, bt_node

            if key in bt_node.keys:
                return self.find_data_util(key,bt_node)
            else:
                return None
        else:
            # match with key if its <= go to left else match with next key, if last go to right
            index = 0
            while index < len(bt_node.keys) and key > bt_node.keys[index]:
                index += 1
            if index < len(bt_node.keys) and key <= bt_node.keys[index]:
                return self.find_rec(key, DISK.read(bt_node.children_addrs[index]),return_index_node)
            else:
                if len(bt_node.children_addrs) == index:
                    index = index - 1
                return self.find_rec(key,  DISK.read(bt_node.children_addrs[index]),return_index_node)

    def find_data_util(self, key: KT, node:BTreeNode) -> Optional[VT]:
        """
        Given a key, retrieve the data associated with that key.
        Returns None if key is not present in self.keys.
        Only valid on leaf nodes.

        Works in logarithmic time using find_idx.
        """
        idx = self.find_idx_util(key, node)
        # We can use the index we would insert at, and check if that entry has the key we need
        if idx < len(node.keys) and node.keys[idx] == key:
            return node.data[idx]
        return None

    def delete(self, key: KT) -> None:
        raise NotImplementedError("Karma method delete()")

    def printNode(self, node):
        print('Keys:', '|'.join([str(y) for y in node.keys]))
        if node.parent_addr:
            print('Parent Keys:', "|".join([str(y) for y in get_node(node.parent_addr).keys]))
        else:
            print('Root')
        print('Index in parent:', node.index_in_parent)
        print('Child keys:', [DISK.read(x).keys for x in node.children_addrs])
        print('')

