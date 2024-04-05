class Node: 
      
    def __init__(self,value = None): 
        self.value=value 
        self.children=[]

    def create(self, dependencies): 
        for dependency in dependencies:    
            first_element, second_element = dependency.split(',')
            
            if second_element == '':
                self.value = first_element
            else:
                node = self.find(second_element)
            
                if node:
                    node.children.append(Node(first_element))
                else:
                    print(f"Non existent node: {second_element}")
   
    def find(self, value):
        if self.value == value:
            # print(f"Value: {root.value}")
            return self

        for child in self.children:
            node = child.find( value)

            if node:
                return node

    def postorder(self):

        yield self
        if len(self.children) != 0:

            for child in self.children:
                yield from child.postorder()

    def length(self, root):   
        if len(root.children) == 0:
            return 1
    
        sum = 0
        for child in root.children:
            sum += self.length(child)
       
        
        return 1 + sum

def round_robin(dependency_root, connections, requests):
    dependency_generator = dependency_root.postorder()
    while True:
        try:
            depdency = next(dependency_generator)
            count +=1
        except:
            print(f"Finished")
            break
        print(f"{depdency}")

    
def read_file(filename):
    dependencies = []
    with open(filename, 'r') as file:
        data_lines = file.readlines()
        
        for data in data_lines:
            dependencies.append(data.strip())
    
    return dependencies

def find_node(root, value):
    if root.value == value:
        # print(f"Value: {root.value}")
        return root

    for child in root.children:
        node = find_node(child, value)
        if node:
            return node

def print_postorder(root):
   
    print(root.value)

    if len(root.children) != 0:
   
        for child in root.children:
            print_postorder(child)

    return

def create_tree(dependencies):

    root = None
    for dependency in dependencies:
        
        first_element, second_element = dependency.split(',')
        
        if second_element == '':
            root = Node(first_element)
        else:
            node = root.find(second_element)
        
            if node:
                node.children.append(Node(first_element))
            else:
                print(f"Non existent node: {second_element}")
        
    return root
if __name__ == "__main__":
    filename = "proj/dependency.csv"

    data = read_file(filename)
    print(data)

    print("\n\n")
    root = Node()

    root.create(dependencies=data)

    print(f"Len: {root.length(root)}")
    connections = {}
    connections[1] = 'a'
    connections[2] = 'a'
    connections[3] = 'a'

    round_robin(root, connections, [])
    
    print("\n\nPrinting tree")
    queried = []

    print(f"querying root: {root.value}")
    for element in root.postorder():
        # print(element.value)
        if len(element.children) == 0:
            if element.value in queried:
                continue
            else:
                print(f'query: {element.value}')
        else:

            print("querying: ", end='')
            for child in element.children:
                print(child.value, end=', ')
                queried.append(child.value)
            print()