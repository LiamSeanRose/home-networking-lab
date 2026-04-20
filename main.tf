resource "proxmox_virtual_environment_vm" "lab_vm" {
  count     = var.vm_count
  name      = "lab-vm-${count.index + 1}"
  node_name = var.proxmox_node

  clone {
    vm_id = var.template_id
  }

  cpu {
    cores = var.vm_cores
    type  = "host"
  }

  memory {
    dedicated = var.vm_memory
  }
  
  agent {
    enabled = true
  }

  disk {
    datastore_id = "local-lvm"
    interface    = "scsi0"
    size         = 40
  }

  network_device {
    bridge = "vmbr0"
  }

  initialization {
    ip_config {
      ipv4 {
        address = "dhcp"
      }
    }
    user_account {
      username = "labadmin"
      keys     = [trimspace(file("~/.ssh/id_rsa.pub"))]
    }
  }

  lifecycle {
    ignore_changes = [initialization]
  }
}

output "vm_names" {
  value = proxmox_virtual_environment_vm.lab_vm[*].name
}

output "vm_ips" {
  value = proxmox_virtual_environment_vm.lab_vm[*].ipv4_addresses
}