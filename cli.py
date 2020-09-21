import argparse
import os

import pandas as pd

from qiime2 import Artifact
from qiime2 import Metadata
from q2_types.feature_data import DNAFASTAFormat

from qiime2.plugins import taxa

def collapse(table, taxonomy):
    for i in range(1, 8):
        _ = taxa.methods.collapse(table=Artifact.load(table),
                                  taxonomy=Artifact.load(taxonomy),
                                  level=i)
        _.collapsed_table.view(pd.DataFrame).T.to_csv(f'level-{i}.csv')

def tax2seq(taxonomy, rep_seqs, output):
    tax_df = Artifact.load(taxonomy).view(pd.DataFrame)

    _ = Artifact.load(rep_seqs)
    f = _.view(DNAFASTAFormat).open()

    features = []
    seqs = []

    for i, line in enumerate(f):
        if i % 2 == 0:
            features.append(line.strip().replace('>', ''))
        else:
            seqs.append(line.strip())

    seq_df = pd.DataFrame({'Feature ID': features, 'Sequence': seqs})
    seq_df = seq_df.set_index('Feature ID')

    _ = pd.concat([tax_df, seq_df], axis=1, sort=False)
    _.to_csv(output)

def make_manifest(fastq_dir, output):
    files = {}

    for r, d, f in os.walk(fastq_dir):
        for x in f:
            name = x.split('_')[0]

            if '_R1_001.fastq' in x:
                if name not in files:
                    files[name] = ['', '']
                files[name][0] = f'{r}/{x}'
            elif '_R2_001.fastq' in x:
                if name not in files:
                    files[name] = ['', '']
                files[name][1] = f'{r}/{x}'
            else:
                pass

    with open(output, 'w') as f:
        headers = ['sample-id', 'forward-absolute-filepath', 
                   'reverse-absolute-filepath']
        f.write('\t'.join(headers) + '\n')

        for name in sorted(files):
            fields = [name, files[name][0], files[name][1]]
            f.write('\t'.join(fields) + '\n')



def add_metadata(metadata, columns, output):
    df1 = Metadata.load(metadata).to_dataframe()
    dtypes = df1.dtypes.to_dict()
    df2 = pd.read_table(columns)

    for k, v in dtypes.items():
        if k in df2.columns:
            if v == 'object':
                df2[k] = df2[k].astype(str)
            else:
                df2[k] = df2[k].astype(v)

    df3 = df1.reset_index().merge(df2).set_index('#SampleID')
    Metadata(df3).save(output)



def main():
    commands = {
        'collapse': collapse,
        'tax2seq': tax2seq,
        'make_manifest': make_manifest,
        'add_metadata': add_metadata,
    }

    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest='command',
                                       metavar='command',
                                       help="Name of the command.")
    subparsers.required = True



    collapse_parser = subparsers.add_parser(
        'collapse',
        description=("This command creates seven collapsed ASV tables, one "
                     "for each taxonomic level. The ouput files (level-1.csv "
                     "through level-7.csv) will be created in the current "
                     "directory."),
        help=("This command creates seven collapsed ASV tables, one for each "
              "taxonomic level."),
    )
    collapse_parser.add_argument(
        'table',
        help="Path to the input table.qza file."
    )
    collapse_parser.add_argument(
        'taxonomy',
        help="Path to the input taxonomy.qza file."
    )



    tax2seq_parser = subparsers.add_parser(
        'tax2seq',
        description=("This command returns the mapping between observed ASVs "
                     "and taxonomic classifications."),
        help=("This command returns the mapping between observed ASVs and "
              "taxonomic classifications."),
    )
    tax2seq_parser.add_argument(
        'taxonomy',
        help="Path to the input taxonomy.qza file."
    )
    tax2seq_parser.add_argument(
        'rep_seqs',
        help="Path to the input rep-seqs.qza file."
    )
    tax2seq_parser.add_argument(
        'output',
        help="Path to the output mapping file (.csv)."
    )



    make_manifest_parser = subparsers.add_parser(
        'make_manifest',
        description=("This command creates a manifest file from a directory "
                     "containing FASTQ files. The file names must include "
                     "either '_R1_001.fastq' or '_R1_002.fastq'. The word "
                     "before the first underscore will be set as the sample "
                     "ID (e.g. 'EXAMPLE' in EXAMPLE_S1_R1_001.fastq.gz)."),
        help=("This command creates a manifest file from a directory "
              "containing FASTQ files."),
    )
    make_manifest_parser.add_argument(
        'fastq_dir',
        help="Path to the directory containing input FASTQ files (.fastq.gz)."
    )
    make_manifest_parser.add_argument(
        'output',
        help="Path to the output manifest file (.tsv)."
    )



    add_metadata_parser = subparsers.add_parser(
        'add_metadata',
        description=("This command adds new columns to an existing "
                     "sample-metadata file. The 'metadata' file and the "
                     "'columns' file must have at least one overlapping "
                     "column."),
        help=("This command adds new columns to an existing sample-metadata "
              "file."),
    )
    add_metadata_parser.add_argument(
        'metadata',
        help="Path to the input sample-metadata.tsv file."
    )
    add_metadata_parser.add_argument(
        'columns',
        help=("Path to a file containing the new columns to be added (.tsv). "
              "The first row should be column names.")
    )
    add_metadata_parser.add_argument(
        'output',
        help="Path to the output sample-metadata.tsv (.tsv)."
    )



    args = parser.parse_args()

    command = args.command

    del args.command

    commands[command](**vars(args))

if __name__ == '__main__':
    main()
