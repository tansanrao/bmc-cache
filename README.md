BMC
===

### __Code for the [NSDI'21 paper](https://www.usenix.org/system/files/nsdi21-ghigoff.pdf) *"BMC: Accelerating Memcached using Safe In-kernel Caching and Pre-stack Processing"*.__

BibTex entry available [here](#cite-this-work).

BMC (BPF Memory Cache) is an in-kernel cache for memcached. It enables runtime, crash-safe extension of the Linux kernel to process specific memcached requests before the execution of the standard network stack. BMC does not require modification of neither the Linux kernel nor the memcached application. Running memcached with BMC improves throughput by up to 18x compared to the vanilla memcached application.

Requirements
---

Linux kernel __v5.3__ or higher is required to run BMC.

Other software dependencies are required to build BMC and Memcached-SR (see [Building BMC](#building-bmc) and [Building Memcached-SR](#building-memcached-sr)). 

Build instructions
---

### Building BMC

This evaluation fork uses current libbpf APIs, BTF map definitions, Linux UAPI
headers, and Clang's BPF target. It was validated with Clang 21 and Linux 7.0.
Install `clang`, `gcc`, `make`, `libelf-dev`, and `zlib1g-dev`. From the parent
Beekeeper repository:

```sh
make -C bmc-cache/bmc
```

The build compiles static libbpf from `linux/tools/lib/bpf`, stages its headers,
and writes `build/bmc/bmc` and `build/bmc/bmc_kern.o`. For a standalone checkout,
pass `LINUX_PATH=/path/to/linux OUTPUT=/path/to/build` to make. Kernel-private
headers, kernel selftests, and the old download/prepare scripts are not needed.

The runtime needs native XDP, BPF syscalls/JIT, and TC support. The parent
Beekeeper repository's `kernelconfig` enables `CONFIG_NET_SCH_INGRESS=y`,
`CONFIG_NET_CLS_BPF=y`, and `CONFIG_NET_ACT_BPF=y`, so its evaluation kernel
needs no separate TC module installation/loading. The BPF action supports
separate actions; the direct-action attachment below uses `cls_bpf`.
For other kernels these options can instead be modules: build/install them
for that kernel, then load `sch_ingress`, `cls_bpf`, and, if built, `act_bpf`.
Configurations missing their built-in dependencies need a rebuilt kernel
and a host-managed VM restart.

### UDP SET evaluation scope

The DurableKV workload uses single-datagram IPv4 UDP GETs and SETs on port
11211. XDP invalidates the hashed cache slot on a UDP `set <key> ...` request;
TC egress fills it from the subsequent userspace `VALUE` reply to a GET.
`STORED` acknowledgements still come exclusively from DurableKV after its WAL
sync. The invalidator reads only the command key, not `set` text in the value.
TCP write invalidation is no longer supported. Preload over TCP **before**
attaching BMC, and do not issue TCP writes while caching is active.

This preserves upstream BMC's coherence limitation: an old GET reply can
refill a slot between SET invalidation and commit, or after commit if the GET
reply was delayed. BMC does not coordinate with DurableKV's WAL/publication.
The benchmark's same-value SETs do not expose this stale-value race; results
are throughput measurements, not a claim of linearizable cache coherence.

The original 3,250,000-slot direct-mapped cache and generic 250-byte key /
1,000-byte value limits are unchanged (about 4.29 GB of cache-map allocation).
Recreate BMC's maps after restarting/recovering the server; do not retain
cached values across an application restart.

With an empty BMC cache and a **disposable** DurableKV server, run from the
remote client `python3 bmc/test_udp.py SERVER_IP`. This writes three keys and
checks changed-value UDP SET invalidation, GET refill/hits, an absent key,
punctuation, and `set` text inside a value. Reconcile its 17 replies with server
and BMC counters: 5 durable SETs, 5 userspace GET hits, 1 miss, 6 XDP hits,
5 cache updates, and 2 invalidations. Do not run it against the measured
benchmark dataset; it deliberately changes values and adds a non-workload key.

### Building Memcached-SR

Memcached-SR is based on memcached v1.5.19. Building it requires the following software:

```sh
clang-9 (or gcc-9) automake libevent-dev
```

Either ```clang-9``` or ```gcc-9``` is required in order to compile memcached without linking issues. Depending on your distribution, you might also need to use the ```-Wno-deprecated-declarations``` compilation flag.

Memcached-SR can be built with the following:
```bash
$ cd memcached-sr 
$ ./autogen.sh
$ CC=clang-9 CFLAGS='-DREUSEPORT_OPT=1 -Wno-deprecated-declarations' ./configure && make
```

The ```memcached``` binary will be located in the memcached-sr directory.

Further instructions
---

### TC egress hook

BMC doesn't attach the tx_filter eBPF program to the egress hook of TC, it needs to be attached manually.

To do so, you first need to make sure that the BPF filesystem is mounted, if it isn't you can mount it with the following command:
```bash
# mount -t bpf none /sys/fs/bpf/
```

After preload, start BMC with the interface index (for example, from the parent
Beekeeper repository, `sudo build/bmc/bmc $(cat /sys/class/net/exp0/ifindex)`).
It attaches native XDP and pins `/sys/fs/bpf/bmc_tx_filter`. The loader refuses
to replace an existing XDP program or pinned filter. In another terminal,
attach the TC program in **direct-action** mode:
```bash
# tc qdisc add dev <interface_name> clsact
# tc filter add dev <interface_name> egress pref 1 handle 1 bpf da object-pinned /sys/fs/bpf/bmc_tx_filter
```

Send `SIGUSR1` to the loader while idle to write `/tmp/bmc_stats.txt`. For
benchmark deltas, read the per-CPU `map_stats` with bpftool before/after each
trial; XDP/driver and physical NIC counters distinguish cache replies from
userspace replies and losses. The upstream `hit_count` is not an exact wire
reply count during invalidation races.

After you are done, remove this experiment's TC attachment, stop the loader
with SIGINT/SIGTERM (which detaches XDP), and unpin the filter. Only remove
`clsact` if this experiment created it and no other filters use it:
```bash
# tc filter del dev <interface_name> egress pref 1 handle 1 bpf
# tc qdisc del dev <interface_name> clsact
```
And unpin the program with ```# rm /sys/fs/bpf/bmc_tx_filter```

License
---

Files under the [bmc](bmc) directory are licensed under the [GNU Lesser General Public License version 2.1](LICENSE).

Files under the [memcached-sr](memcached-sr) directory are licensed under the [BSD-3-Clause BSD](LICENSE&#32;(Memcached&#32;customizations)) license.

Cite this work
---
BibTex:
```
@inproceedings{265047,
	title        = {{BMC}: Accelerating Memcached using Safe In-kernel Caching and Pre-stack Processing},
	author       = {Yoann Ghigoff and Julien Sopena and Kahina Lazri and Antoine Blin and Gilles Muller},
	year         = 2021,
	month        = apr,
	booktitle    = {18th {USENIX} Symposium on Networked Systems Design and Implementation ({NSDI} 21)},
	publisher    = {{USENIX} Association},
	pages        = {487--501},
	isbn         = {978-1-939133-21-2},
	url          = {https://www.usenix.org/conference/nsdi21/presentation/ghigoff}
}
```
