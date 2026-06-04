variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "Base name for all resources"
  type        = string
  default     = "rag-api"
}

variable "environment" {
  description = "Deployment environment: dev, staging, prod"
  type        = string
  default     = "prod"
}

variable "api_image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "anthropic_api_key_secret_arn" {
  description = "ARN of the Secrets Manager secret containing ANTHROPIC_API_KEY"
  type        = string
}

variable "voyage_api_key_secret_arn" {
  description = "ARN of the Secrets Manager secret containing VOYAGE_API_KEY"
  type        = string
}

variable "app_api_key_secret_arn" {
  description = "ARN of the Secrets Manager secret containing the X-API-Key value"
  type        = string
}
