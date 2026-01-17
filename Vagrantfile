# -*- mode: ruby -*-
# vi: set ft=ruby :

# yolo-cage VM configuration
#
# This Vagrantfile creates an Ubuntu 22.04 VM with yolo-cage fully installed.
#
# Usage:
#   vagrant up                 # Create and provision the VM
#   vagrant ssh                # SSH into the VM
#   vagrant provision          # Re-run provisioning (idempotent)
#   vagrant destroy -f         # Delete the VM
#
# After provisioning:
#   vagrant ssh
#   yolo-cage-configure        # Configure with your GitHub credentials
#   yolo-cage create my-branch # Create a pod

Vagrant.configure("2") do |config|
  # Ubuntu 22.04 LTS (Jammy)
  config.vm.box = "ubuntu/jammy64"

  # VM configuration
  config.vm.hostname = "yolo-cage"

  # Network configuration
  # Forward kubectl proxy port (useful for debugging)
  config.vm.network "forwarded_port", guest: 8001, host: 8001

  # Forward dispatcher port (for external API access)
  config.vm.network "forwarded_port", guest: 30080, host: 30080

  # Provider-specific configuration
  config.vm.provider "virtualbox" do |vb|
    vb.name = "yolo-cage"
    vb.memory = 8192  # 8GB RAM
    vb.cpus = 4

    # Enable nested virtualization (might be needed for some operations)
    vb.customize ["modifyvm", :id, "--nested-hw-virt", "on"]
  end

  # Libvirt provider (for Linux hosts using KVM)
  config.vm.provider "libvirt" do |lv|
    lv.memory = 8192
    lv.cpus = 4
    lv.nested = true
  end

  # Sync the yolo-cage directory into the VM
  config.vm.synced_folder ".", "/home/vagrant/yolo-cage"

  # Provisioning script
  config.vm.provision "shell", inline: <<-SHELL
    set -e

    echo "=========================================="
    echo "yolo-cage VM Provisioning"
    echo "=========================================="
    echo ""

    # Run the build script
    cd /home/vagrant/yolo-cage
    sudo -u vagrant ./scripts/build-release.sh

    echo ""
    echo "=========================================="
    echo "Provisioning complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "  1. vagrant ssh"
    echo "  2. yolo-cage-configure --init"
    echo "  3. Edit ~/.yolo-cage/config.yaml with your credentials"
    echo "  4. yolo-cage-configure"
    echo "  5. yolo-cage create my-branch"
    echo ""
  SHELL

  # Post-up message
  config.vm.post_up_message = <<-MSG
    yolo-cage VM is ready!

    Connect with:
      vagrant ssh

    Then configure yolo-cage:
      yolo-cage-configure --init
      # Edit ~/.yolo-cage/config.yaml
      yolo-cage-configure

    Create your first pod:
      yolo-cage create my-feature-branch
      yolo-cage attach my-feature-branch
  MSG
end
