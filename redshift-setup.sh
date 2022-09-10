 echo "Running setup script on redshift"
 AWS_ID=$(aws sts get-caller-identity --query Account --output text | cat)
echo "CREATE EXTERNAL SCHEMA last
FROM DATA CATALOG DATABASE 'lastdb' iam_role 'arn:aws:iam::"$AWS_ID":role/sde-spectrum-redshift' CREATE EXTERNAL DATABASE IF NOT EXISTS;
DROP TABLE IF EXISTS last.loan_tracker;
CREATE EXTERNAL TABLE last.loan_tracker (
    loan_category VARCHAR(100),
    count BIGINT,
    insert_date VARCHAR(12)
) STORED AS PARQUET LOCATION 's3://afroga-project/stage/loan_tracker/';
" > ./redshift_setup.sql

psql -f ./redshift_setup.sql postgres://sde_user:sdeP0ssword0987@sde-batch-project.cgbocxyapou5.us-west-1.redshift.amazonaws.com:5439/dev
rm ./redshift_setup.sql


