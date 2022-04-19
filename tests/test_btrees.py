from py_btrees.disk import DISK
from py_btrees.btree import BTree
from py_btrees.btree_node import BTreeNode, get_node

import pytest
from typing import Any
import random

# This is a rewriting of all of the specifications that the handout provides,
# except it does not test the property that all leaf nodes reside at the same level.
# Note that fulfilling all of these requirements does NOT guarantee a working BTree.
def btree_properties_recurse(root_node_addr, node, M, L):

    assert sorted(node.keys) == node.keys # Keys should remain sorted so that a binary search is possible

    if node.is_leaf:
        # Leaf node general properties
        assert len(node.children_addrs) == 0
        assert len(node.keys) == len(node.data)
        assert len(node.data) <= L
    else:
        # Non-leaf node general properties
        assert len(node.data) == 0
        assert len(node.keys) == len(node.children_addrs) - 1
        assert len(node.children_addrs) <= M

    if node.my_addr == root_node_addr:
        # Root node properties
        assert node.parent_addr is None
        assert node.index_in_parent is None
        if not node.is_leaf:
            assert len(node.children_addrs) >= 2
    else:
        # Non-root node properties
        print('nonroot')
        assert node.parent_addr is not None
        assert node.parent_addr == node.get_parent().my_addr
        assert node.index_in_parent is not None
        assert node.get_parent().children_addrs[node.index_in_parent] == node.my_addr
        if node.is_leaf:
            assert len(node.data) >= (L+1)//2
        else:
            assert len(node.children_addrs) >= (M+1)//2
        
    # Run the assertions on all children
    for child_addr in node.children_addrs:
        btree_properties_recurse(root_node_addr, DISK.read(child_addr), M, L)

#Calculate the max height of BTree
def get_max_height(node: BTreeNode) -> int:
    if node.is_leaf:
        return 0
    max_height = float('-inf')
    for i in node.children_addrs:
        child = get_node(i)
        max_height = max(get_max_height(child), max_height)
    return max_height + 1

#Calculate the min height of BTree
def get_min_height(node: BTreeNode) -> int:
    if node.is_leaf:
        return 0
    min_height = float('inf')
    for i in node.children_addrs:
        child = get_node(i)
        min_height = min(get_min_height(child), min_height)
    return min_height + 1

#Calculate the min height of BTree
def get_min_height(node: BTreeNode) -> int:
    if node.is_leaf:
        return 0
    min_height = float('inf')
    for i in node.children_addrs:
        child = get_node(i)
        min_height = get_min_height(child)

def test_btree_properties() -> None:
    M = 5
    L = 3
    btree = BTree(M, L)
    for i in range(100):
        btree.insert(i, str(i))
    for i in range(0, -100):
        btree.insert(i, str(i))

    root_addr = btree.root_addr

    btree_properties_recurse(root_addr, DISK.read(root_addr), M, L)



# If you want to run tests with various parameters, lookup pytest fixtures
def test_insert_and_find_odd():
    M = 3
    L = 3
    btree = BTree(M, L)
    btree.insert(0, "0")
    btree.insert(1, "1")
    btree.insert(2, "2")
    btree.insert(3, "3") # SPLIT!
    btree.insert(4, "4")

    root = DISK.read(btree.root_addr)
    assert not root.is_leaf
    assert len(root.keys) == 1
    assert root.keys[0] in [1, 2] # the split must divide the data evenly, so the key will be 1 or 2 depending on how you represent the keys array
    assert len(root.children_addrs) == 2
    left_child = DISK.read(root.children_addrs[0])
    right_child = DISK.read(root.children_addrs[1])

    assert left_child.is_leaf
    assert right_child.is_leaf
    assert right_child.parent_addr == root.my_addr
    assert right_child.index_in_parent == 1
    for key in left_child.keys:
        assert key in [0, 1]
    for key in right_child.keys:
        assert key in [2, 3, 4]

    assert btree.find(0) == "0"
    assert btree.find(4) == "4"

def test_insert_and_find_even():
    M = 2
    L = 2
    btree = BTree(M, L)
    btree.insert(0, "0")
    btree.insert(1, "1")
    btree.insert(2, "2") # SPLIT!

    root = DISK.read(btree.root_addr)
    assert not root.is_leaf
    assert len(root.keys) == 1
    assert root.keys[0] in [0, 1, 2] # You can divide the data into [0] [1 2] or [0 1] [2], so since the keys representation could mean left or right, it can be 0, 1, or 2
    assert len(root.children_addrs) == 2
    left_child = DISK.read(root.children_addrs[0])
    right_child = DISK.read(root.children_addrs[1])

    assert left_child.is_leaf
    assert right_child.is_leaf
    for key in left_child.keys:
        assert key in [0, 1]
    for key in right_child.keys:
        assert key in [1, 2]

    assert btree.find(0) == "0"
    assert btree.find(2) == "2"

def test_insert_and_find_edge():
    M = 2
    L = 1
    btree = BTree(M, L)
    btree.insert(0, "0")
    btree.insert(1, "1") # SPLIT!

    root = DISK.read(btree.root_addr)
    assert not root.is_leaf
    assert len(root.keys) == 1
    assert root.keys[0] in [0, 1]
    assert len(root.children_addrs) == 2
    left_child = DISK.read(root.children_addrs[0])
    right_child = DISK.read(root.children_addrs[1])

    assert left_child.is_leaf
    assert right_child.is_leaf
    for key in left_child.keys:
        assert key in [0]
    for key in right_child.keys:
        assert key in [1]

    assert btree.find(0) == "0"
    assert btree.find(1) == "1"

def test_btree_properties_random_stepbystep() -> None:
    M = random.randint(2, 10)
    L = random.randint(1, 10)
    btree = BTree(M, L)
    a = [i for i in range(-1000, 1001, 1)]
    random.shuffle(a)

    for j, i in enumerate(a):
        btree.insert(str(i), str(i))
        assert str(i) == btree.find(str(i))
        root_addr = btree.root_addr
        btree_properties_recurse(root_addr, DISK.read(root_addr), M, L)

    root_addr = btree.root_addr
    btree_properties_recurse(root_addr, DISK.read(root_addr), M, L)


def test_btree_properties_100_stepbystep() -> None:
    M = 5
    L = 3
    btree = BTree(M, L)
    for i in range(100):
        btree.insert(i, str(i))
        assert str(i) == btree.find(i)
        root_addr = btree.root_addr
        btree_properties_recurse(root_addr, DISK.read(root_addr), M, L)
    for i in range(-1, -100, -1):
        btree.insert(i, str(i))
        assert str(i) == btree.find(i)
        root_addr = btree.root_addr
        btree_properties_recurse(root_addr, DISK.read(root_addr), M, L)

    root_addr = btree.root_addr
    btree_properties_recurse(root_addr, DISK.read(root_addr), M, L)

def test_btree_properties_random_stepbystep() -> None:
    M = random.randint(2, 10)
    L = random.randint(1, 10)
    btree = BTree(M, L)
    a = [i for i in range(-1000, 1001, 1)]
    random.shuffle(a)

    for j, i in enumerate(a):
        btree.insert(str(i), str(i))
        assert str(i) == btree.find(str(i))
        root_addr = btree.root_addr
        btree_properties_recurse(root_addr, DISK.read(root_addr), M, L)

    root_addr = btree.root_addr
    btree_properties_recurse(root_addr, DISK.read(root_addr), M, L)

def test_random_10_stepbystep():
    for _ in range(10):
	    test_btree_properties_random_stepbystep()

def test_root_2_children() -> None:
    M = 5
    L = 3
    btree = BTree(M, L)
    for i in range(100):
        btree.insert(i, str(i))
    for i in range(0, -100):
        btree.insert(i, str(i))

    root_addr = btree.root_addr
    root_node = get_node(root_addr)

    assert len(root_node.children_addrs) >=2

def test_same_level_leaves() -> None:
    M = 5
    L = 3
    btree = BTree(M, L)
    for i in range(100):
        btree.insert(i, str(i))
    for i in range(0, -100):
        btree.insert(i, str(i))
    root_addr = btree.root_addr
    root_node = get_node(root_addr)
    max = get_max_height(root_node)
    min = get_min_height(root_node)
    assert max == min

#Caution. It takes a lot of time
def test_highest_L() -> None:
    M = 2
    L = 99999
    btree = BTree(M, L)
    for i in range(99999*3):
        btree.insert(i, str(i))
    for i in range(0, -99999*3):
        btree.insert(i, str(i))

    root_addr = btree.root_addr

    btree_properties_recurse(root_addr, DISK.read(root_addr), M, L)

def test_highest_M() -> None:
    M = 99999
    L = 1000
    btree = BTree(M, L)
    for i in range(99999):
        btree.insert(i, str(i))
    for i in range(0, -99999):
        btree.insert(i, str(i))

    root_addr = btree.root_addr

    btree_properties_recurse(root_addr, DISK.read(root_addr), M, L)

def get_random_M():
    return random.randint(2, 99999)

def get_random_L():
    return random.randint(1, 99999)

def generate_M_L_pairs(n:int):
    pairs = []
    for i in range(n):
        pairs.append(tuple([get_random_M(), get_random_L()]))
    return pairs

def test_different_M_L_pairs():
    number_of_pairs = 10
    pairs = generate_M_L_pairs(number_of_pairs)
    while pairs:
        M, L = pairs.pop()
        btree = BTree(M, L)

        keys = [i for i in range(-1000, 1001, 1)]
        random.shuffle(keys)

        for i in keys:
            btree.insert(i, str(i))

        root_addr = btree.root_addr
        root_node = get_node(root_addr)
        assert get_max_height(root_node) == get_min_height(root_node)
        btree_properties_recurse(root_addr, DISK.read(root_addr), M, L)