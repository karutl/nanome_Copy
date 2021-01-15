"""

Evaluation based on methylation calls of four tools, compute the performance results(F1, accuracy, etc.)

/projects/li-lab/NanoporeData/WR_ONT_analyses/NanoCompare/automated_DeepSignal_runs/NA19240/NA19240_DeepSignal.MethCalls.Joined.tsv /projects/li-lab/NanoporeData/WR_ONT_analyses/NanoCompare/automated_Tombo_runs/NA19240/NA19240_Tombo.batch_all.batch_0.perReadsStats.bed /projects/li-lab/NanoporeData/WR_ONT_analyses/NA19240_nanopolish/NA19240.methylation_calls.tsv /projects/li-lab/NanoporeData/WR_ONT_analyses/NanoCompare/automated_DeepMod_runs/NA19240/NA19240.C.combined.bed /projects/li-lab/NanoporeData/WR_ONT_analyses/NanoCompare/EncodeMethyl/joined_reps/RRBS/extractBismark/NA19240_joined_RRBS.Read_R1.Rep_1_trimmed_bismark_bt2.bismark.cov.gz NA19240_RRBS_joined/NA19240_RRBS_joined bismark 10 Tombo


"""
import argparse

"""
   This script will generate all performance results, bed files of singleton, non-singleton, based on results by DL call tool related to BGTruth results
"""

# this script was based on this jupyter notebook: http://helix067:9912/notebooks/li-lab/NanoporeData/WR_ONT_analyses/ai/GitHub/nanoCompare/Scripts/UniversalMethStatsEvaluation.ipynb
# copied Wed Jul 10 14:27:33 EDT 2019
# example command run: python /projects/li-lab/NanoporeData/WR_ONT_analyses/ai/GitHub/nanoCompare/Scripts/UniversalMethStatsEvaluation.standalone_01.py $DeepSignal_calls $Tombo_calls $Nanopolish_calls $bgTruth $RunPrefix $parser

# where variable names came from:
# DeepSignal_calls = importPredictions_DeepSignal(argv[1])#"/projects/li-lab/NanoporeData/WR_ONT_analyses/NanoCompare/automated_DeepSignal_runs/K562/K562_DeepSignal.MethCalls.Joined.chr20.tsv")
# Tombo_calls = importPredictions_Tombo(argv[2])#"/projects/li-lab/NanoporeData/WR_ONT_analyses/NanoCompare/automated_Tombo_runs/K562/K562_Tombo.perReadsStats.chr20.bed")
# Nanopolish_calls = importPredictions_Nanopolish_2(argv[3])#"/projects/li-lab/NanoporeData/WR_ONT_analyses/Leukemia_ONT/K562.nanopolish/K562.methylation_calls.chr_chr20.tsv", IncludeNonSingletons = True)
# bgTruth = importGroundTruth_BedMethyl_from_Encode(argv[4])#"/projects/li-lab/NanoporeData/WR_ONT_analyses/NanoCompare/EncodeMethyl/K562/ENCSR765JPC_WGBS_hg38/ENCFF721JMB.bed", chrFilter="chr20")
# RunPrefix = argv[5]#"K562_WGBS_rep_ENCFF721JMB/K562_WGBS_rep_ENCFF721JMB"
# parser = "encode"

####################

# nanocompare_prj = "/projects/li-lab/yang/workspace/nano-compare/src"
# sys.path.append(nanocompare_prj)

from nanocompare.global_settings import singletonsFile, narrowCoord, nonsingletonsFile, perf_table_column_list
from nanocompare.meth_stats.meth_stats_common import *

from nanocompare.global_config import *


def parse_arguments():
    """
    :return:
    """
    parser = argparse.ArgumentParser(description='Performance evaluation task')

    parser.add_argument('--min-cov', type=int, help="min coverage cutoff", default=5)
    parser.add_argument('--dsname', type=str, help="dataset name", default='DS')
    parser.add_argument('--runid', type=str, help="running prefix", required=True)
    parser.add_argument('--report-joined', action='store_true', help="True if report on only joined sets")
    parser.add_argument('--calls', nargs='+', help='all ONT call results <tool-name>:<file-name>', required=True)
    parser.add_argument('--bgtruth', type=str, help="background truth file <encode-type>:<file-name>", required=True)
    parser.add_argument('-o', type=str, help="output dir", default=pic_base_dir)

    #
    # parser.add_argument('--sep', type=str, help="seperator for output csv file", default=',')
    # parser.add_argument('--processors', type=int, help="running processors", default=8)
    # parser.add_argument('--bgtruthcov-cutoff', type=int, help="cutoff of coverage in bg-truth", default=10)
    # parser.add_argument('--toolcov-cutoff', type=int, help="cutoff of coverage in nanopore calls", default=4)
    # parser.add_argument('--baseFormat', type=int, help="cutoff of coverage in nanopore calls", default=0)

    return parser.parse_args()


if __name__ == '__main__':
    set_log_debug_level()

    args = parse_arguments()

    RunPrefix = args.runid

    out_dir = os.path.join(args.o, args.runid)
    os.makedirs(out_dir, exist_ok=True)
    logger.info(f'Output to dir:{out_dir}')

    # Add logging files also to result output dir
    add_logging_file(os.path.join(out_dir, 'run-results.log'))

    logger.debug(args)

    # Note: all bed files (Singleton and NonSingleton) are 1-based start, even for "chr1  123  124" (This will conform for + or - strand).
    # So we must import as 1-based format for our tool or bgtruth, DO NOT USE baseFormat=0
    baseFormat = 1

    report_joined = args.report_joined

    minCov = args.min_cov

    dsname = args.dsname

    callfn_dict = defaultdict()  # callname -> filename
    callresult_dict = defaultdict()  # name->call
    callname_list = []  # [DeepSignal, DeepMod, etc.]

    # with Pool(processes=args.processors) as pool:
    for callstr in args.calls:
        callname, callfn = callstr.split(':')
        callname_list.append(callname)
        callfn_dict[callname] = callfn
        callresult_dict[callname] = import_call(callfn, callname, baseFormat=baseFormat)
        # callresult_dict[callname] = pool.apply_async(import_call, (callfn, callname,))

    logger.debug(callfn_dict)
    encode, fn = args.bgtruth.split(':')
    logger.debug(f'BGTruth fn={fn}, encode={encode}')

    bgTruth = import_bgtruth(fn, encode, cov=minCov, baseFormat=baseFormat, includeCov=True)

    relateCoord = list(narrowCoord)  # copy the basic coordinate

    ## add missing region files:
    singletonsFilePrefix = singletonsFile.replace(".bed", '')
    # relateCoord.append("{}/{}.{}.mixed.bed".format(out_dir, RunPrefix, singletonsFilePrefix))
    relateCoord.append(f"{out_dir}/{RunPrefix}.{singletonsFilePrefix}.absolute.bed")

    nonsingletonsFilePrefix = nonsingletonsFile.replace(".bed", '')
    # relateCoord.append("{}/{}.{}.other.bed".format(out_dir, RunPrefix, nonsingletonsFilePrefix))
    # relateCoord.append("{}/{}.{}.fullyMixed.bed".format(out_dir, RunPrefix, nonsingletonsFilePrefix))
    relateCoord.append(f"{out_dir}/{RunPrefix}.{nonsingletonsFilePrefix}.discordant.bed")
    relateCoord.append(f"{out_dir}/{RunPrefix}.{nonsingletonsFilePrefix}.concordant.bed")

    logger.debug(list(enumerate(relateCoord)))  # all coordinate generated

    post_process = True
    if post_process:
        ret = singletonsPostprocessing(bgTruth, singletonsFile, RunPrefix, outdir=out_dir)
        ret.update(nonSingletonsPostprocessing(bgTruth, nonsingletonsFile, RunPrefix, outdir=out_dir))
        df = pd.DataFrame([ret], index=f'{RunPrefix}')
        outfn = os.path.join(out_dir, f'{RunPrefix}.summary.singleton.nonsingleton.csv')
        df.to_csv(outfn)
        logger.info(f'save to {outfn}')

    logger.info("\n\n############\n\n")

    # this file is the all tool joined together sites
    fn_secondFilterBed = f"{out_dir}/{RunPrefix}.Tools_BGTruth_Joined.bed"

    # this file is used for all coverage > 4 for correlation analysis
    fn_secondFilterBed_4Corr = f"{out_dir}/{RunPrefix}.Tools_BGTruth_Joined.4Corr.bed"

    joinedCPG = set(bgTruth.keys())
    for toolname in callresult_dict:
        joinedCPG = joinedCPG.intersection(set(callresult_dict[toolname].keys()))
    # logger.info(f'joinedCPG = {len(joinedCPG)}')
    save_keys_to_single_site_bed(joinedCPG, outfn=fn_secondFilterBed, callBaseFormat=baseFormat, outBaseFormat=1)

    logger.info(f"Data points for joined all tools(cov>={minCov}) with bg-truth stats: {len(joinedCPG):,}\n\n")

    joinedCPG4Corr = combine2programsCalls_4Corr(bgTruth, None, only_bgtruth=True)
    for toolname in callresult_dict:
        joinedCPG4Corr = combine2programsCalls_4Corr(joinedCPG4Corr, callresult_dict[toolname])

    joinedCPG4CorrSet = set(joinedCPG4Corr.keys())
    save_keys_to_single_site_bed(joinedCPG4CorrSet, outfn=fn_secondFilterBed_4Corr, callBaseFormat=baseFormat, outBaseFormat=1)

    logger.info(f"Data points for correlation tools(cov>={minCov}) with bg-truth(cov>=4): {len(joinedCPG4CorrSet):,}\n\n")
    logger.info("\n\n############\n\n")

    if report_joined:  # Joined together evaluation
        perf_dir = os.path.join(out_dir, 'performance-results')
        os.makedirs(perf_dir, exist_ok=True)
    else:  # only based on bgtruth
        perf_dir = os.path.join(out_dir, 'performance-results-nojoined')
        os.makedirs(perf_dir, exist_ok=True)

    for tool in callresult_dict:
        tmpPrefix = f'{RunPrefix}.{tool}'
        logger.info(f'Evaluating: {tmpPrefix}')

        # Note: relateCoord - all singleton (absolute and mixed) and non-singleton generated bed. ranges
        #       secondFilterBed - joined sites of four tools and bg-truth. points
        if report_joined:  # step: with joined results of all tools
            df = report_per_read_performance(callresult_dict[tool], bgTruth, tmpPrefix, narrowedCoordinatesList=relateCoord, secondFilterBed=fn_secondFilterBed, secondFilterBed_4Corr=fn_secondFilterBed_4Corr)
        else:  # step: no joined results
            df = report_per_read_performance(callresult_dict[tool], bgTruth, tmpPrefix, narrowedCoordinatesList=relateCoord, secondFilterBed=False, secondFilterBed_4Corr=fn_secondFilterBed_4Corr)
        df = df[perf_table_column_list]

        df['Tool'] = tool
        df['Dataset'] = dsname

        outfn = os.path.join(perf_dir, f"{RunPrefix}.{tool}.report.tsv")
        df.to_csv(outfn, sep='\t')
        logger.info(f"save to {outfn}")
    logger.info("Meth stats performance data generation DONE.")
