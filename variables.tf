variable "proxmox_endpoint" {
  type        = string
  description = "Proxmox API endpoint URL"
  default     = "https://192.168.1.4:8006/"
}

variable "proxmox_api_token" {
  type        = string
  description = "Proxmox API token in format: user@realm!tokenid=secret"
  sensitive   = true
}

variable "proxmox_node" {
  type    = string
  default = "pve"
}

variable "vm_count" {
  type    = number
  default = 1
}

variable "vm_memory" {
  type    = number
  default = 12288
}

variable "vm_cores" {
  type    = number
  default = 6
}

variable "template_id" {
  type        = number
  description = "VM ID of the cloud-init template to clone from"
  default     = 9000
}