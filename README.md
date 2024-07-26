# Algorithmisches Beweisen Lab

Thorsten Kroehl

## Allgemeines 
 Wurde in Python 3.10.12 ( Ubuntu Standard 22.04) geschrieben. \
 Cadical Style Output Formate und Programm Exits.
 Um die Submodules zu nutzen:
 ```
git submodule update --init --recursive
cd cadical
./configure && make
cd ../drat-trim
make
 ```


## KNF Generierung

### Random

 description='Generate random (n, c, k)-CNF in DIMACS format' \
 'n', type=int, help='Number of variables' \
 'c', type=int, help='Number of clauses' \
 'k', type=int, help='Clause size' \
'--output', '-o', default='output.cnf', help='Output file name (default: output.cnf)'

### Pebbling 
description='Generate pebbling cnf in DIMACS format' \
'n', type=int, help='Number of variables' \
'--output', '-o', default='output.cnf', help='Output file name (default: output.cnf)'


### PHP
description='Generate php cnf in DIMACS format' \
'n', type=int, help='Number of variables' \
'--output', '-o', default='output.cnf', help='Output file name (default: output.cnf)'

## Algorithmen

### 2SAT
description='Implements 2-Sat Algorithm' \
'--input', '-i', default='input.cnf', help='Input file name (default: input.cnf)'

### DP 
description='Implements DP Algorithm' \
'--input', '-i', default='input.cnf', help='Input file name (default: input.cnf)'

### DPLL
description='Implements DPLL Algorithm' \
'--pure', '-p', action='store_true', help='Enable Pure Literal Elimination' \
'--input', '-i', default='input.cnf', help='Input file name (default: input.cnf)'

### CDCL

description='Implements CDCL Algorithm' \
'--input', '-i', default='input.cnf', help='Input file name (default: input.cnf)' \
'--vsids', '-v', action='store_true', help='Enable VSIDS Heuristic' \
'--restarts', '-r', action='store_true', help='Enable Restarts' \
'--learn', '-l', action='store_true', help='Enable Clause Learning' \
'--delete', '-d', action='store_true', help='Enable Clause Deletion' \
'--minimize', '-m', action='store_true', help='Enable Clause Minimalization' \

Wenn UNSATISFIABLE dann wird Prrof File unsat.drat ausgegeben.

## Benchmarks

Zum Testen von DPLL und CDCL wurde ein kelines Testprogramm geschrieben ```test_comparison.py```.
Hier Wird geschaut ob Cadical denselben exit code hat.
Zusätzlich wird falls cdcl ausgeführt wird das .drat file mit drat trim überprüft.

Um neue Bilder für die Benchmark Markdown zu generieren:
```
 python3 benchmark.py  -t 10
``` 
(-t = Anzahl an läufen für random, php und pebbling werden nur einmal ausgeführt)
```
 python3 visualize.py 
```

