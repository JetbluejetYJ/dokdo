# dokdo

```dokdo``` is a collection of scripts for microbiome sequencing analysis. For details, please see the Wiki page. Pull requests are welcome.

# Command Line Interface (CLI)

For getting help:

```
$ python3 /path/to/dokdo/cli.py -h
usage: cli.py [-h] command ...

positional arguments:
  command         Name of the command.
    collapse      This command creates seven collapsed ASV tables, one for
                  each taxonomic level.
    tax2seq       This command returns the mapping between observed ASVs and
                  taxonomic classifications.
    make_manifest
                  This command creates a manifest file from a directory
                  containing FASTQ files.
    add_metadata  This command adds new columns to an existing sample-metadata
                  file.
    merge_metadata
                  This command merges two or more sample-metadata.tsv files
                  vertically.

optional arguments:
  -h, --help      show this help message and exit
(qiime2-2020.8) SEUNGs-MacBook-Pro-2:Desktop seung
```

For getting command-specific help:

```
$ python3 /path/to/dokdo/cli.py add_metadata -h
usage: cli.py add_metadata [-h] metadata columns output

This command adds new columns to an existing sample-metadata file. The
'metadata' file and the 'columns' file must have at least one overlapping
column.

positional arguments:
  metadata    Path to the input sample-metadata file (.tsv).
  columns     Path to a file containing the new columns to be added (.tsv).
              The first row should be column names.
  output      Path to the output sample-metadata file (.tsv).

optional arguments:
  -h, --help  show this help message and exit
```