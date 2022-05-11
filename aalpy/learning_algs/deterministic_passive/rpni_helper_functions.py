import pickle

class RpniNode:
    __slots__ = ['output', 'children', 'prefix']

    def __init__(self, output):
        self.output = output
        self.children = dict()
        self.prefix = ()

    def copy(self):
        return pickle.loads(pickle.dumps(self, -1))

    def __lt__(self, other):
        return len(self.prefix) < len(other.prefix)

    def __le__(self, other):
        return len(self.prefix) <= len(other.prefix)

    def __eq__(self, other):
        return self.prefix == other.prefix


def check_sequance(root_node, seq, automaton_type):
    curr_node = root_node
    for i, o in seq:
        if i not in curr_node.children.keys():
            return False
        curr_node = curr_node.children[i]
        if automaton_type != 'mealy' and curr_node.output != o:
            return False
    return True


def createPTA(data, automaton_type):
    root_node = RpniNode(None)
    for seq in data:
        curr_node = root_node
        for i, o in seq:
            if i is None and seq.index((i,o)) == 0:
                if root_node.output is not None and o != root_node.output:
                    return None
                root_node.output = o
                continue
            if automaton_type == 'mealy':
                i = (i, o)
            if i not in curr_node.children.keys():
                node = RpniNode(o)
                node.prefix = curr_node.prefix + (i,)
                curr_node.children[i] = node
            else:
                if curr_node.children[i].output != o:
                    return None
            curr_node = curr_node.children[i]
    return root_node


def extract_unique_sequences(root_node):
    def get_leaf_nodes(root_node):
        leaves = []

        def _get_leaf_nodes(node):
            if node is not None:
                if len(node.children.keys()) == 0:
                    leaves.append(node)
                for n in node.children.values():
                    _get_leaf_nodes(n)

        _get_leaf_nodes(root_node)
        return leaves

    leaf_nodes = get_leaf_nodes(root_node)
    paths = []
    for node in leaf_nodes:
        seq = []
        curr_node = root_node
        for i in node.prefix:
            curr_node = curr_node.children[i]
            seq.append((i, curr_node.output))
        paths.append(seq)

    return paths


def to_automaton(red, automaton_type):
    from aalpy.automata import DfaState, Dfa, MooreMachine, MooreState, MealyMachine, MealyState

    if automaton_type == 'dfa':
        state, automaton = DfaState, Dfa
    elif automaton_type == 'moore':
        state, automaton = MooreState, MooreMachine
    else:
        state, automaton = MealyState, MealyMachine

    initial_state = None
    prefix_state_map = {}
    for i, r in enumerate(red):
        if automaton_type != 'mealy':
            prefix_state_map[r.prefix] = state(f's{i}', r.output)
        else:
            prefix_state_map[r.prefix] = state(f's{i}')
        if i == 0:
            initial_state = prefix_state_map[r.prefix]

    for r in red:
        for i, c in r.children.items():
            if automaton_type != 'mealy':
                prefix_state_map[r.prefix].transitions[i] = prefix_state_map[c.prefix]
            else:
                prefix_state_map[r.prefix].transitions[i[0]] = prefix_state_map[c.prefix]
                prefix_state_map[r.prefix].output_fun[i[0]] = i[1]

    return automaton(initial_state, list(prefix_state_map.values()))


def visualize_pta(rootNode):
    from pydot import Dot, Node, Edge
    graph = Dot('fpta', graph_type='digraph')

    graph.add_node(Node(str(rootNode.prefix), label=f'{rootNode.output}'))

    queue = [rootNode]
    visited = set()
    visited.add(rootNode.prefix)
    while queue:
        curr = queue.pop(0)
        for i, c in curr.children.items():
            if c.prefix not in visited:
                graph.add_node(Node(str(c.prefix), label=f'{c.output}'))
            graph.add_edge(Edge(str(curr.prefix), str(c.prefix), label=f'{i}'))
            if c.prefix not in visited:
                queue.append(c)
            visited.add(c.prefix)

    graph.add_node(Node('__start0', shape='none', label=''))
    graph.add_edge(Edge('__start0', str(rootNode.prefix), label=''))

    graph.write(path=f'pta.pdf', format='pdf')


def test_rpni_with_eq_oracle(model, num_samples = 10000):
    import random
    from aalpy.SULs import MealySUL
    from aalpy.learning_algs.deterministic_passive.RPNI import RPNI
    from aalpy.oracles import RandomWalkEqOracle

    input_al = model.get_input_alphabet()

    dfa_sul = MealySUL(model)
    data = []
    for _ in range(10000):
        dfa_sul.pre()
        seq = []
        for _ in range(5, 20):
            i = random.choice(input_al)
            o = dfa_sul.step(i)
            seq.append((i, o))
        dfa_sul.post()
        data.append(seq)

    rpni_model = RPNI(data, automaton_type='dfa').run_rpni()

    eq_oracle_2 = RandomWalkEqOracle(input_al, dfa_sul, num_steps=10000)
    cex = eq_oracle_2.find_cex(rpni_model)
    if cex is None:
        print(rpni_model.size, model.size)
        print("Could not find a counterexample between RPNI and original model.")
    else:
        print('Counterexample found. Either RPNI data was incomplete, or there is a bug in RPNI algorithm :o ')
