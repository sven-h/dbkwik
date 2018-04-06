cimport cython
from libc.stdio cimport FILE, fopen,fdopen, fclose, fread
from libc.string cimport memchr, memcpy
from libcpp cimport bool
from libcpp.string cimport string


#https://stackoverflow.com/questions/6874102/python-strings-in-a-cython-extension-type
cdef class Resource:
    cdef public str value # or object ? str
    def __init__(self, c):
        self.value = str(c)#TODO: hack for working in pyton2 /linux? self.value = c

    def __repr__(self):
        return "<" + self.value + ">"
    def __str__(self):
        return "<" + self.value + ">"


cdef class Literal:
    cdef public str value
    cdef public str extension

    def __init__(self, lex, ext):
        self.value = str(lex)#TODO: hack for working in pyton2 /linux?
        self.extension = str(ext)#TODO: hack for working in pyton2 /linux?

    def __repr__(self):
        return '"' + self.value + '"' + self.extension
    def __str__(self):
        return '"' + self.value + '"' + self.extension



def parse(file_like):
    if not hasattr(file_like, "read"):
        raise ValueError("no read function available")
    cdef char buf[8388609]
    buf_py = file_like.read(8388609)#file_like.read(16384) # 2^23 + 1   ~ 8MB
    cdef int bytes_read = len(buf_py)
    memcpy(buf,<char*>buf_py, bytes_read)

    cdef int line_count = 0
    cdef char* linestart = buf
    cdef char* lineend = NULL
    cdef char* current = NULL
    cdef char* startNode = NULL
    cdef bool last_line = False
    cdef int copy_amount = 0
    cdef str literal_lexical

    while not last_line:
        my_list = []
        lineend = <char*>memchr(<void*>linestart, '\n', (buf + bytes_read) - linestart)
        if lineend == NULL:
            copy_amount = (buf + bytes_read) - linestart
            memcpy(buf, linestart, copy_amount)
            buf_py = file_like.read(8388609 - copy_amount)
            if not buf_py:
                #no more to read
                last_line = True
                #print("BBBBLLLAAA")
                #print(copy_amount)
                lineend = buf + copy_amount
                #print(buf)
                #print(lineend)
            else:
                bytes_read = len(buf_py)
                memcpy(buf + copy_amount,<char*>buf_py, bytes_read)
                bytes_read += copy_amount
                linestart = buf

                lineend = <char*>memchr(<void*>linestart, '\n', (buf + bytes_read) - linestart)
                if lineend == NULL:
                    last_line = True
                    lineend = buf + bytes_read

        #process this line
        #print("<Line>")
        #print(lineend[-1:])
        #print(linestart)
        #print(linestart[:lineend-linestart])
        #print("</Line>")

        line_count += 1
        current = linestart
        while True:
            if current[0] == '\n' or current >= lineend: # or current[0] == '\n' or current >= lineend)and len(my_list) == 0: # empty line
                #print("newline or over line")
                if len(my_list) > 0:
                    raise ValueError("Couldn't find . in line " + str(line_count))
                break
            elif current[0] == ' ' or current[0] == '\t':
                current += 1
            elif current[0] == '<':
                #resource
                #print("Resource")
                current += 1
                startNode = current
                current = <char*>memchr(<void*>current, '>', lineend - current)
                if current == NULL:
                    raise ValueError("Could not find closing '>' bracket for resource in line " + str(line_count))
                my_list.append(Resource(startNode[:current - startNode]))#.decode('UTF-8')  #TODO: hack for working in pyton2 /linux? prev: my_list.append(Resource(startNode[:current - startNode].decode('UTF-8')))
                current += 1
            elif current[0] == '.':
                #statment end
                #print("statment end")
                if len(my_list) == 0:
                    raise ValueError("No nodes but statement end in line" + str(line_count))
                yield my_list
                break
            elif current[0] == '"':
                #literal
                #print("literal")
                current += 1
                startNode = current
                while True:
                    current = <char*>memchr(<void*>current, '"', lineend - current)
                    if current == NULL:
                        raise ValueError('Could not find closing " for literal in line ' + str(line_count))
                    #print("next:")
                    #print(current)
                    if current[-1] != '\\':
                        break
                    i = -1
                    while current[i] == '\\':
                        i = i - 1
                    if (i+1) % 2 == 0:
                        break
                    current += 1
                literal_lexical = str(startNode[:current - startNode])#TODO: hack for working in pyton2 /linux?   prev: literal_lexical = startNode[:current - startNode].decode('UTF-8')
                current += 1

                #find literal extension
                #print("Extensionm:")
                startNode = current
                #print(startNode)
                while not ((current[0] == '.' and (current[1] == ' ' or (current + 2) >= lineend )) or current[0] == ' '):
                    current += 1
                #print(current)
                #print(startNode[:current - startNode].decode('UTF-8'))
                my_list.append(Literal(literal_lexical, startNode[:current - startNode]))#TODO: hack for working in pyton2 /linux? startNode[:current - startNode].decode('UTF-8')
                #print("HAllo")
                #print(current)
                #print(current)
            elif current[0] == '#': # or current[0] == '\n' or current >= lineend)and len(my_list) == 0: # empty line
                #print("comment")
                if len(my_list) > 0:
                    raise ValueError("Couldn't find . in line " + str(line_count))
                break
            else:
                raise ValueError("Exception: Wrong starting character in line " + str(line_count))

            if current >= lineend:
                if len(my_list) == 0:
                    #print("Empty line: " +str(line_count))
                    break
                else:
                    raise ValueError("Couldn't find . in line " + str(line_count) + ":" + str(my_list))

        linestart = lineend + 1


