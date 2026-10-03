import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')

cmd = """
python3 -c '
import struct

with open("/Applications/League of Legends.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient", "rb") as f:
    magic = f.read(4)
    print("Magic:", magic.hex())
    if magic in (b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"):
        nfat = struct.unpack(">I", f.read(4))[0]
        print(f"Fat binary with {nfat} architectures:")
        for i in range(nfat):
            cputype, cpusubtype, offset, size, align = struct.unpack(">IIIII", f.read(20))
            arch = "x86_64" if cputype == 0x01000007 else ("ARM64" if cputype == 0x0100000c else f"cpu_{cputype:x}")
            print(f"  [{i}] {arch}: offset=0x{offset:x} ({offset}), size=0x{size:x} ({size})")
'
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
