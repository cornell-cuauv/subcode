#!/usr/bin/env python3

import argparse
import subprocess

def to_shm_name(name):
    res = [name[0].lower()]
    for idx, c in enumerate(name[1:]):
        if c in ('ABCDEFGHIJKLMNOPQRSTUVWXYZ') \
                and not (idx > 0 and (name[idx-1] in ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))):
            res.append('_')
            res.append(c.lower())
        else:
            res.append(c)
    return ''.join(res)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('writable_shm_group')
    parser.add_argument('readable_shm_group')
    parser.add_argument('port_directory')
    args = parser.parse_args()

    result = subprocess.run(
            ['auv-serial', 'info', args.port_directory], 
            stdout=subprocess.PIPE
    )

    output = result.stdout.decode('utf-8').split('\n')
    output = filter(lambda x: 'Name' not in x, output)
    output = list(filter(lambda x: 'Type' not in x, output))

    writables = []
    readables = []
    mode = 'writable'
    
    for item in output:
        if 'writable' in item.lower():
            mode = 'writable' 
            continue
        elif 'readable' in item.lower():
            mode = 'readable'
            continue
        
        processed = item.strip('\t')
        processed = processed.split(' ')
        processed = list(filter(lambda x: x != '', processed)) 
        if len(processed) == 0:
            continue 
    
        if mode == 'writable':
            writables.append(processed)
        else:
            readables.append(processed)
    
    for item in writables:
        print(f"{item[1]} = {args.writable_shm_group}.{to_shm_name(str(item[1]))}")
    for item in readables:
        print(f"{item[1]} = {args.readable_shm_group}.{to_shm_name(str(item[1]))}")
