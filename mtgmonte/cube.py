# Funcs for cube statistics


x = """
40  dual lands
10  tri lands
40 white # -5
39 green #
36 black
45 blue # -5
40 red # -5
48 uncommons
36 gold
52 rares
"""

sum([int(y.split(' ')[0]) for y in x.split('\n')[1:-1]])
sum([int(y.split(' ')[0]) for y in x.split('\n')[1:-1]]) - 360
