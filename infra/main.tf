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
  default = ["dev", "prod"]
}

# DEFECT: count over a list. Remove the middle environment and read the plan.
# Today's session measured exactly what this does.
resource "aws_s3_bucket" "env" {
  for_each = toset(var.environments)
  bucket   = "${var.student}-capstone-${each.key}"
}

resource "aws_security_group" "api" {
  name        = "${var.student}-capstone-api"
  description = "capstone api"

  # DEFECT: the whole internet can reach SSH on this box.
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["127.0.0.1/32"]
  }

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

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

resource "aws_lambda_function" "ingest" {
  function_name = "${var.student}-capstone-ingest"
  filename      = "${path.module}/handler.zip"
  role          = aws_iam_role.lambda_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
}

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.env["dev"].arn
}

resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.env["dev"].id

  lambda_function {
    lambda_function_arn = aws_lambda_function.ingest.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

output "buckets" {
  value = [for bucket in aws_s3_bucket.env : bucket.bucket]
}
