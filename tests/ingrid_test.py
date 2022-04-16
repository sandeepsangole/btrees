import random
from py_btrees.btree import BTree
import graph

def insert_and_find_odd():
    M = 5
    L = 3
    btree = BTree(M, L)
    for i in range(12):
        btree.insert(i, str(i))

    # btree.insert(12, '123')
    g = graph.create(btree)
    # print(g.source)
    g.view()
    # for i in range(0, -100):
    #     btree.insert(i, str(i))

    # g = graph.create(btree)
    # # print(g.source)
    # g.view()

insert_and_find_odd()