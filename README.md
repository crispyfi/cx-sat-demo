# AOS-CX Systems Acceptance Testing Demo

<div align=left markdown>
<a href="https://codespaces.new/crispyfi/cx-sat-demo?quickstart=1">
<img src="https://gitlab.com/rdodin/pics/-/wikis/uploads/d78a6f9f6869b3ac3c286928dd52fa08/run_in_codespaces-v1.svg?sanitize=true" style="width:50%"/></a>

**[Run](https://codespaces.new/crispyfi/cx-sat-demo?quickstart=1) this lab in GitHub Codespaces for free**.  
[Learn more](https://containerlab.dev/manual/codespaces) about Containerlab for Codespaces.  
<small>Machine type: 4 vCPU · 16 GB RAM</small>
</div>

The lab consists of a VSX pair of virtual AOS-CX switches and two Linux hosts to demonstrate testing using [Robot Framework](https://robotframework.org/) for AOS-CX.

A full library of test cases is available at [crispyfi/robotframework-aos-cx](https://github.com/crispyfi/robotframework-aos-cx)

More information about running virtual AOS-CX switches with Containerlab in GitHub Codespaces is available at [crispyfi/clab-aos-cx-demo](https://github.com/crispyfi/clab-aos-cx-demo)

## Running tests

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

---