# pyspark
import argparse

from pyspark.sql import SparkSession
from pyspark.sql.functions import lit
from pyspark.sql.functions import *


def main(
    input_loc: str, output_loc: str, run_id: str
) -> None:
    """
    This is a function to track the number of loans in each loan category of a bank using
    the following steps
        1. collect inputed data
        2. read and track each loan category
        3. write data to a HDFS output

    """

    # input dataset
    df = spark.read.option("header", True).csv(input_loc)

    # number of loans present in each category
    loan_category = spark.createDataFrame(
        sorted(df.groupBy('loan_category').count().collect()))

    loan_tracker = loan_category.withColumn("insert_date", lit(run_id))

    # parquet is a popular column storage format, we use it here
    loan_tracker.write.mode("overwrite").parquet(output_loc)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", type=str, help="HDFS input", default="/loan"
    )
    parser.add_argument(
        "--output", type=str, help="HDFS output", default="/output"
    )
    parser.add_argument("--run-id", type=str, help="run id")

    args = parser.parse_args()
    spark = SparkSession.builder.appName(
        "Loan tracker"
    ).getOrCreate()
    main(
        input_loc=args.input, output_loc=args.output, run_id=args.run_id
    )
