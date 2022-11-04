import sys
arg = [ib_split_ports]
out = []
for s in arg:
    a, b, *_ = map(int, s.split('-') * 2)
    out.extend(map(str, range(a, b+1)))

print(out)     