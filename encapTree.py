def checkSafety(x):
    def checkSanitation(*args, **kwargs):
        output = x(*args, **kwargs)
        for byte in reservedBytes:
            if byte in output:
                raise RuntimeError(f'Uncaught {byte} returned from {x.__name__}, args: {args}, kwargs: {kwargs}')
        return output 
    return checkSanitation

def intpushup(x,vals):
    for val in vals:
        if x>=val:
            x+=1
    return x
def intpushdown(x,vals):
    for val in vals[::-1]:
        if x>val:
            x-=1
    return x

def cleanData(x):
    def sanitized(*args, **kwargs):
        rawoutput=list(x(*args, **kwargs))
        rawoutput=changeBase(rawoutput,256,256-len(reservedBytes))
        rawoutput=[intpushup(x,reservedBytes) for x in rawoutput]
        return bytes(rawoutput)
    return sanitized
def fromCleanedData(x):
    rawval=list(x)
    rawval=[intpushdown(x,reservedBytes) for x in rawval]
    rawval=changeBase(rawval,256-len(reservedBytes),256)
    return bytes(rawval)

def changeBase(x,a,b):
    x=sum([y*a**i for i,y in enumerate(x[::-1])])
    o=[]
    if x==0:
        return [0]
    while x>0:
        o.append(x%b)
        x=x//b
    o=o[::-1]
    return o
    

@checkSafety
@cleanData
def getBytes(x):
    if type(x)==int:
        if x==0:
            return b''
        bytelen=1+(x.bit_length())//8 #bit length + 1 divided by 8 rounded up
        return x.to_bytes(bytelen,'big',signed=True)
    if type(x)==str:
        return x.encode()
    if type(x)==bool:
        return bytes([x])
    if type(x)==float:
        return x.hex().encode('ascii')
def fromBytes(x,dtype):
    x=fromCleanedData(x)
    if dtype==int:
        return int.from_bytes(x,"big",signed=True)
    if dtype==str:
        return x.decode("utf-8")
    if dtype==bool:
        return bool.from_bytes(x,"big")

def encode(struct):
    raw=inner_encode(struct)
    raw=raw[1:-1]
    raw=raw.lstrip(b'(')
    for key,value in replacements.items():
        raw=raw.replace(key,value)
    return raw

def decode(raw):
    for value,key in list(replacements.items())[::-1]:
        raw=raw.replace(key,value)
    push=0
    for byte in raw:
        if byte==b')'[0]:
            push+=1
        elif byte==b'('[0]:
            push-=1
    raw=b'('*push+raw
    code=b'('+raw+b')'
    stack=[]
    for byte in code:
        if byte == b')'[0]:
            ind=stack.index(b'('[0])
            stack=[stack[:ind]]+stack[ind+1:]
        else:
            stack.insert(0,byte)
    stack=stack[0]
    return inner_decode(stack)

def inner_decode(struct):
    struct=struct[::-1]
    dtype=struct[0]
    data=struct[1:]
    if dtype==0:
        dtype=bool
        data=False
    elif dtype==1:
        dtype=bool
        data=True
    else:
        for key,value in typePrefix.items():
            if value==bytes([dtype]):
                dtype=key
                break
        else:
            raise TypeError(f'Unknown type {dtype}')
    if dtype == bool:
        return data
    if dtype in [int,str,float]:
        return fromBytes(bytes(data),dtype)
    elif dtype in [list,set,tuple]:
        return dtype([inner_decode(x) for x in data])
    elif dtype == dict:
        raw=[inner_decode(x) for x in data]
        return dtype([(raw[2*i],raw[2*i+1]) for i in range(len(raw)//2)])
    else:
        raise TypeError(f'Unsupported type {dtype}')

def inner_encode(struct):
    global typePrefix
    if type(struct) in [int,str,bool,float]:
        return b'('+typePrefix[type(struct)]+getBytes(struct)+b')'
    elif type(struct) in [list,set,tuple]:
        return b'('+typePrefix[type(struct)]+b''.join([inner_encode(x) for x in struct])+b')'
    elif type(struct) == dict:
        out=b'('+typePrefix[type(struct)]
        for key,value in struct.items():
            out+=inner_encode(key)+inner_encode(value)
        out+=b')'
        return out
        
    elif False:
        raise NotImplementedError(f'Type {type(struct)} is not yet supported')
    else:
        raise TypeError(f'Unsupported type {type(struct)}')

reservedBytes=[b'(',b')',b',',b'{',b'}',b'|']
replacements={b')(':b',',b'),(':b'|',b'((':b'{',b'))':b'}'}

typePrefix = {
    bool: b'', #Booleans arent type annotated, but their value will never be a type thus a \x00 or \x01 is always a boolean if found in the type location
    int:  b'\x02',
    str:  b'\x03',
    float:b'\x04',
    dict: b'\x05',
    list: b'\x06',
    tuple:b'\x07',
    set:  b'\x08',}

reservedBytes=sorted([byte[0] for byte in reservedBytes])

tests = \
    ['hi',
     'bye',
     1,
     2,
     10023,
     True,
     False,
     ['what', 'no', '1', 1, 'bye', 'pls'],
     [['nothin', 'personal'], ['what', 'no'], 'yes'],
     {1:2, 'hi': 'bye', 1:'hi', 2:'bye'},
     [['more', ['nested']], ['lists'], 'because', 'tests'],
     {('well', 'this'): 'is awkward', 'because': ['i', 'said', 'so']},
     {'a', 'b', 'c', 1, 2, 3},
     [{'exception': 'Getting data from server failed'}, {'exception': 'Getting data from server failed'},
      {'exception': 'Getting data from server failed'}, {'exception': 'Getting data from server failed'}],
     [{'exception': 'Getting data from server failed', 'xception': ('Getting data from server failed','test')},
      {'exception': 'Getting data from server failed'}, {'exception': 'Getting data from server failed'}],
     (('gaw',
  {'metar': 'METAR: `UGSB 151830Z 13005KT 9999 FEW030 25/25 Q1015 NOSIG`',
   'player_count': '26 player(s) online',
   'players': [('Eagle 6-1 | primehc', 'Unknown'),
               ('Mischief 1-1', 'Unknown'),
               ('Sting 3-6 | Trueforce538', 'Unknown'),
               ('2d', 'Unknown'),
               ('Panther 1-1 | Jester', 'Unknown'),
               ('Jager 1-2 | MatchstickTV', 'Unknown'),
               ('Wulf 1-1 | Wulfblitzer', 'Unknown'),
               ('RAZOR 1-1 | Ace', 'Unknown'),
               ('Whiplash 1-1', 'Unknown'),
               ('WASP', 'Unknown'),
               ('Rainman', 'Unknown'),
               ('MAKO 1-1', 'Unknown'),
               ('Norwank 1-1 | Sack', 'Unknown'),
               ('Lt.MonkeyBrain[NL]', 'Unknown'),
               ('LowestOfGround', 'Unknown'),
               ('USA hel 3 unit1', 'Unknown'),
               ('Blacksheep 1-8 | Moojuice', 'Unknown'),
               ('AcrylicNinja', 'Unknown'),
               ('phantom_bora', 'Unknown'),
               ('Solar 1-1', 'Unknown'),
               ('spooker 1-1|hossein', 'Unknown'),
               ('Savage 1-1 | Whiplash', 'Unknown'),
               ('Pirate 5-0', 'Unknown'),
               ('Razor 1-2 | VET', 'Unknown'),
               ('419 | Noble 2 (the 2nd)', 'Unknown')],
   'restart': 'restart <t:1692142907:R>'}),
 ('pgaw', {'exception': 'Getting data from server failed'}),
 ('lkeu',
  {'player_count': '1 player(s) online',
   'players': [('LK Admin', 'Unknown'), ('Cobalt 1-2 | Mythic', 'Unknown')],
   'restart': 'restart <t:1692141320:R>'}),
 ('lkna',
  {'player_count': '0 player(s) online',
   'players': [('LK Admin', 'Unknown')],
   'restart': 'restart <t:1692157163:R>'}))]
for test in tests:
    enc=encode(test)
    dec=decode(enc)
    if test!=dec:
        print('Test Failed:',repr(test),'decoded as',repr(dec))
    else:
        print("Test Passed")
