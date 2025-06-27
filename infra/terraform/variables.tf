variable "do_token" {
  type        = string
  description = "DigitalOcean API token"
}

variable "region" {
  type        = string
  description = "DO region, e.g. fra1"
  default     = "fra1"
}
