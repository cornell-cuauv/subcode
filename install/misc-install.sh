# **************** zsh ****************

apt-get -y install zsh

# The stacks should be mounted at /home/software/cuauv/software
rm /home/software/.bashrc

sudo -u software tee /home/software/.zshrc <<'EOF'

if [[ $TERM = "dumb" ]]; then
    bash && exit
fi

if [[ -f /home/software/.env ]]; then
   . /home/software/.env
fi
. /home/software/.zshrc_user
EOF

sudo -u software ln -s /home/software/cuauv/software/install/zshrc /home/software/.zshrc_user

ZSH=/home/software/.oh-my-zsh
sudo -u software git clone --depth=1 https://github.com/robbyrussell/oh-my-zsh.git "${ZSH}"
# cp $ZSH/templates/zshrc.zsh-template /home/software/.zshrc
chsh -s $(grep /zsh$ /etc/shells | tail -1) software

# **************** ssh ****************

apt-get -y install openssh-server sshfs

echo "PermitEmptyPasswords yes" | tee -a /etc/ssh/sshd_config
echo "PasswordAuthentication yes" | tee -a /etc/ssh/sshd_config
echo "X11UseLocalhost no" | tee -a /etc/ssh/sshd_config
echo "UsePAM yes" | tee -a /etc/ssh/sshd_config

echo "auth sufficient pam_permit.so" > /etc/pam.d/sshd

sudo -u software mkdir -p /home/software/.ssh

sudo -u software tee /home/software/.ssh/config <<'EOF'
Host loglan
  Hostname cuauv.org
  Port 2222
  User software
  ForwardX11 yes
  ForwardX11Timeout 20d
  ForwardX11Trusted yes
EOF

# **************** vim ****************
sudo -u software mkdir -p /home/software/.config
sudo -u software ln -s /home/software/cuauv/software/install/nvim /home/software/.config/

# **************** mypy ****************
sudo -u software ln -s /home/software/cuauv/software/install/mypy /home/software/.config/

# **************** sloth ****************

mkdir -p /build_tmp_sloth

cd /build_tmp_sloth
git clone https://github.com/alexrenda/sloth.git sloth

cd sloth

python3 setup.py install

rm -rf /build_tmp_sloth

# **************** sloth ****************

mkdir -p /tmp/ueye
pushd /tmp/ueye

apt-get -y install libqt5gui5 

if [[ "$(uname -m)" == "x86_64" ]]; then
    #wget https://cuauv.org/nix-res-private/uEye-Linux-4.90.06-64.tgz
    curl https://resources.cuauv.org/uEye-Linux-4.90.06-64.tgz -o /tmp/uEye-Linux-4.90.06-64.tgz
    tar -xvf /tmp/uEye-Linux-4.90.06-64.tgz
    ./ueyesdk-setup-4.90.06-eth-amd64.gz.run
fi


mkdir /var/log/auv && chown software /var/log/auv & chgrp software /var/log/auv

# **************** ueye ****************

mkdir -p /usr/local/share/ueye/ueyeethd/

cat > /usr/local/share/ueye/ueyeethd/ueyeethd.conf << 'EOF'
;Ni1
[Parameters]
 Interfaces = eth0

[eth0]
 Port_Base = 50000
EOF

# **************** git-lfs ****************

# ubuntu 20/22 cannot install newer versions of git-lfs, this command makes it possible
curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
apt-get -y install git-lfs
git lfs install

# **************** vscode online **********
curl -fsSL https://code-server.dev/install.sh | sh

# *************** ZED *********************

if [[ $(uname -a | grep "tegra") ]]; then
    cd /usr/local/zed/resources/
    curl -O https://resources.cuauv.org/neural_depth_3.6.model
    curl -O https://resources.cuauv.org/.neural_depth_3.6.model_optimized-fbcbl-1-87-12020-8904-8602-8-128-4096-48-164-512-8-1-0e53-512
fi


