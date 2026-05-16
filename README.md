# AOS-CX Systems Acceptance Testing Demo

<div align=left markdown>
<a href="https://codespaces.new/crispyfi/cx-sat-demo?quickstart=1">
<img src="https://gitlab.com/rdodin/pics/-/wikis/uploads/d78a6f9f6869b3ac3c286928dd52fa08/run_in_codespaces-v1.svg?sanitize=true" style="width:50%"/></a>

**[Run](https://codespaces.new/crispyfi/cx-sat-demo?quickstart=1) this lab in GitHub Codespaces for free**.  
[Learn more](https://containerlab.dev/manual/codespaces) about Containerlab for Codespaces.  
<small>Machine type: 4 vCPU · 16 GB RAM</small>
</div>

---

The lab consists of a VSX pair of virtual AOS-CX switches and two Linux hosts to demonstrate testing using [Robot Framework](https://robotframework.org/) for AOS-CX.

A full library of test cases is available at [crispyfi/robotframework-aos-cx](https://github.com/crispyfi/robotframework-aos-cx)

More information about running virtual AOS-CX switches with Containerlab in GitHub Codespaces is available at [crispyfi/clab-aos-cx-demo](https://github.com/crispyfi/clab-aos-cx-demo)

Find out more about [Containerlab labs in Codespaces](https://containerlab.dev/manual/codespaces/).

This lab also uses the [Containerlab VS Code Extension](https://containerlab.dev/manual/vsc-extension/).

## Lab Topology

The lab topology consists of:
- A VSX pair of core AOS-CX switches (`core-01` and `core-02`)
- A Linux host connected to each switch, in separate VLANs

| Hostname | IP Address     | VLAN ID | Gateway     |
| -------- | -------------- | ------- | ----------- |
| host-01  | 10.32.10.10/24 | 10      | 10.32.10.1  |
| host-02  | 10.32.20.10/24 | 20      | 10.32.20.1  |

The topology is defined in [`topology.clab.yml`](topology.clab.yml).

## Pre-requisites

In order to use this lab, you'll need to create and host the container image for the AOS-CX Switch Simulator in a private GitHub Container Registry, since it is not publicly available.
This can be done using the forked vrnetlab project [hellt/vrnetlab](https://github.com/hellt/vrnetlab) to 'package' the AOS-CX image in a Docker container that can be run in containerlab.

1. Create your own [GitHub account](https://github.com/signup) if you don't have one
2. Fork [this repository](https://github.com/crispyfi/cx-sat-demo)
3. Run the [Build & Push ArubaOS-CX Docker Image](.github/workflows/ova-to-docker.yml) workflow.
   You will need to provide a URL for the AOS-CX Switch Simulator image you want to use.
   This URL can be obtained from <https://networkingsupport.hpe.com> when downloading the image in your browser.
   The workflow builds the image and pushes it to `ghcr.io/<your-username>/arubaos-cx` (tagged with both the detected version and `latest`).
4. Install VS Code on your local machine
5. Set your default editor to Visual Studio Code in [Codespaces settings](https://github.com/settings/codespaces)

## Starting the lab

Use the **Run in Codespaces** button at the top of this README to create a new Codespaces machine and open it remotely in VS Code. If you don't have the GitHub Codespaces extension you'll be prompted to install it and authorize access to your GitHub account.

Once the Codespace has launched, open the Containerlab extension and deploy the lab from the `topology.clab.yml` file.

The logs should show the switch image being pulled from ghcr.io:

```
[stderr] 03:31:42 INFO Pulling ghcr.io/crispyfi/arubaos-cx:latest Docker image
[stderr] 03:32:31 INFO Done pulling ghcr.io/crispyfi/arubaos-cx:latest
```

## Running tests

Open up a terminal in VSCode to run the following commands or use `--help` to see all available options.

```sh
uv run python verify.py -a                                  # all devices
uv run python verify.py -d clab-cx-sat-demo-core-01         # CORE-01 only
uv run python verify.py -d clab-cx-sat-demo-core-02         # CORE-02 only
```

## Output

Each test run drops its artefacts into `output/<hostname>/<YYYYMMDD-HHMMSS>/`. 

To view the results, run the following command and then open the forwarded port 8080 URL from the **Ports** tab in VS Code:
```bash
python3 -m http.server 8080 --directory /workspaces/cx-sat-demo/output
```

Open `log.html` for the per-keyword report with full request/response details, or `report.html` for the pass/fail summary.

## Troubleshooting from Claude Code (MCP)

`mcp_server.py` is an [MCP](https://modelcontextprotocol.io) server that lets Claude Code troubleshoot the switches directly.

When you open this repo in Claude Code, the server is picked up automatically from `.mcp.json` — approve it when prompted (use `/mcp` to view or manage servers). Dependencies are installed by `uv sync`.

Switch credentials are read from the repo's `.env` file:

```sh
CX_USERNAME=admin
CX_PASSWORD=admin
```

Two tools are exposed:

- `list_devices` — switch hostnames and IPs from `site.yaml`
- `check_vsx` — runs the VSX ISL, keepalive, and firmware checks against one switch

Then just ask, e.g. *"List the devices, then check VSX health on CORE-01"*.

---