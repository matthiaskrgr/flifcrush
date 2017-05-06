# flifcrush
## bruteforce flif optimizer

### Usage

````
flifcrush.py [-h] [-i] [-n] [-d] [-c] N1 N2 N3 [Nx ...]
````

````
  N                  file(s) or path (recursively) to be converted to flif

optional arguments:
  -h, --help         show help message and exit
  -i, --interlace    force interlacing (default: find out best)
  -n, --nointerlace  force interlacing off (default: find out best)
  -d, --debug        print output of all runs at end
  -c, --compare      compare to default flif compression
````

#### Example
````
 ./flifcrush.py -c samples/FreedroidRPG.png
````

![Usage Example](https://raw.githubusercontent.com/matthiaskrgr/flifcrush/master/samples/screenshot.png)
