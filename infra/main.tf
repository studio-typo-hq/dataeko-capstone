terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}

# Everything points at LocalStack. No real AWS account, no real money.
provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  # Without this, Terraform addresses buckets as http://<bucket>.localhost:4566
  # which never resolves, and apply hangs instead of failing.
  s3_use_path_style = true

  endpoints {
    s3     = "http://localhost:4566"
    lambda = "http://localhost:4566"
    iam    = "http://localhost:4566"
    ec2    = "http://localhost:4566"
    logs   = "http://localhost:4566"
  }
}

variable "student" {
  type        = string
  description = "your github username, lowercase"
}

variable "environments" {
  type    = list(string)
  default = ["dev", "staging", "prod"]
}

resource "aws_s3_bucket" "env" {
  for_each = toset(var.environments)
  bucket   = "${var.student}-capstone-${each.value}"
}

resource "aws_security_group" "api" {
  name        = "${var.student}-capstone-api"
  description = "capstone api"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Phase 6.3: IAM role for Lambda execution
resource "aws_iam_role" "lambda_role" {
  name = "${var.student}-capstone-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Phase 6.3: Ingest Lambda Function
resource "aws_lambda_function" "ingest" {
  filename         = "${path.module}/handler.zip"
  function_name    = "${var.student}-capstone-ingest"
  role             = aws_iam_role.lambda_role.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  source_code_hash = filebase64sha256("${path.module}/handler.zip")
}

# Phase 6.3: Grant S3 permission to invoke the Lambda function
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.env["dev"].arn
}

# Phase 6.3: S3 bucket notification on dev bucket
resource "aws_s3_bucket_notification" "dev_notification" {
  bucket = aws_s3_bucket.env["dev"].id

  lambda_function {
    lambda_function_arn = aws_lambda_function.ingest.arn
    events              = ["s3:ObjectCreated:*"]
  }

  # depends_on ensures the Lambda invoke permission exists before S3 verifies the target
  depends_on = [aws_lambda_permission.allow_s3]
}

output "buckets" {
  value = [for bucket in aws_s3_bucket.env : bucket.bucket]
}
