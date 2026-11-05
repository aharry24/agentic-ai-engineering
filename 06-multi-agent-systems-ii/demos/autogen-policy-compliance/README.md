# AutoGen Multi-Agent Document Compliance Checker

A multi-agent system built with [AutoGen (AG2)](https://github.com/ag2ai/ag2) that reviews internal company documents for compliance problems, rates their severity, and routes each one to the right reviewer with an action item and a due date. Think of it as an automated document QA team that never sleeps.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/<your-username>/<your-repo>/blob/main/AutoGen_Document_Compliance.ipynb)

## How it works

Four agents work together in an AutoGen `GroupChat`, coordinated by a `GroupChatManager` that picks who speaks next:

| Agent | Role |
|---|---|
| **DocumentScanner** | Extracts metadata (ID, title, type, last updated) and categorizes each document as HR, Technical, or Operational |
| **ComplianceChecker** | Finds issues such as missing sections, missing signatures, and outdated references, and rates each as Critical, Major, or Minor |
| **ReviewCoordinator** | Routes each document by severity and sets due dates, then produces a routing table and an audit trail |
| **UserProxy** | Stands in for the human user and starts the workflow |

```
New documents ──► DocumentScanner ──► ComplianceChecker ──► ReviewCoordinator ──► Summary report
                    (metadata)          (issues + severity)    (routing + deadlines)
```

### Routing rules

| Severity | Routed to | Due in |
|---|---|---|
| 🔴 Critical | Legal / Executive review | 3 days |
| 🟠 Major | Department head | 14 days |
| 🟡 Minor | Document owner | 30 days |

### Design choices

- **Clear agent roles.** Each agent's system message says what it must *not* do, so agents don't overlap.
- **A fixed output format.** The ReviewCoordinator must return one table with exactly six columns, so the result can be read by code.
- **Automatic stop.** The ReviewCoordinator ends its message with `TERMINATE`, which tells both the UserProxy and the manager to stop. The run doesn't need anyone to type anything.
- **A summary built from the run.** The final report reads the ReviewCoordinator's message from the chat history and shows its routing table. It counts documents by severity by finding the Severity column from the table's header row, so the count still works if the model changes how it fills the other columns. Nothing in the summary is hard-coded.
- **Consistent results.** Setting `temperature: 0` makes severity ratings and findings repeatable from run to run, and in testing it stopped the model inventing issues that weren't there.

## Sample documents

The notebook includes three sample documents, each with problems planted on purpose:

- **DOC001: Employee Remote Work Policy (HR).** Has no approval section and refers to superseded 2021 guidelines.
- **DOC002: Data Security Manual (Technical).** Is missing its Incident Response and Data Retention sections.
- **DOC003: Customer Service Guidelines (Operational).** Has no signature and no review date, and relies on a 2019 handbook.

## Run it

1. Open the notebook in Google Colab (use the badge above, or upload `AutoGen_Document_Compliance.ipynb`).
2. Click the 🔑 **Secrets** icon in the left sidebar, add `OPENAI_API_KEY` with your OpenAI key, and turn on **Notebook access**.
3. Choose **Runtime → Run all**.

The notebook uses `gpt-4o-mini` with `temperature: 0`, and one run costs a fraction of a cent. To use a different model, change `"model"` in Step 3.

### Run locally instead

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="your-key"
jupyter notebook AutoGen_Document_Compliance.ipynb
```

If Colab Secrets aren't available, the notebook asks for the key in a hidden input box.

## Example output

From a run on 2026-11-05 with `gpt-4o-mini` at `temperature: 0`. The chat finished in 4 turns.

```
📊 COMPLIANCE WORKFLOW SUMMARY
============================================================
Documents Processed: 3
Chat turns: 4

Documents by severity:
  🔴 Critical: 1
  🟠 Major: 2
  🟡 Minor: 0
```

**Routing decisions from the ReviewCoordinator:**

| Document | Issues | Severity | Routing Decision | Action Items | Due Date |
|---|---|---|---|---|---|
| DOC001 | Missing Required Sections, Outdated References | Major | Route to department head for approval | Include an approval section with signatures and specify a review date; clarify changes from 2021 guidelines | 2026-11-19 |
| DOC002 | Missing Required Sections | Critical | Immediate escalation to Legal/Executive review | Add the missing sections: Incident Response Procedures and Data Retention Policy | 2026-11-08 |
| DOC003 | Missing Required Sections, Inconsistent Terminology | Major | Route to department head for approval | Include necessary signatures for approval and specify a review date; update reference to the most current handbook | 2026-11-19 |

Each document is rated by its most serious issue. DOC001 and DOC003 each have one Major and one Minor issue, so both are routed as Major with a 14-day deadline. The full agent conversation is saved in the notebook's output.

## Known limitations

- **Results can vary.** `temperature: 0` makes runs much more consistent, but not exactly the same every time. In earlier runs at the default temperature, the severities moved between documents (one run rated DOC002 Major and DOC003 Critical).
- **The model can get facts wrong.** One earlier run claimed DOC001 had no effective date, although the document states "Effective Date: January 2023." Setting `temperature: 0` stopped that mistake in later runs, but the agents' findings should still be checked by a person before anyone acts on them.
- **Issue labels are the model's judgment.** In the example above, the outdated 2019 handbook was labelled "Inconsistent Terminology" when "Outdated References" fits better.

## Possible extensions

- Feed `create_custom_compliance_rules()` into the ComplianceChecker so each document type is checked against its own required sections and maximum age
- Load real documents (PDF, DOCX, Markdown) from a folder instead of the sample list
- Replace the `setup_monitoring_webhook()` stub with a real webhook that runs the workflow whenever a document is created or updated
- Save the routing table to CSV or send it to a ticketing tool

## Tech stack

Python · AutoGen (AG2) · OpenAI API · Google Colab

## Credits

Based on *Lesson 01, Demo 02: Using AutoGen for Autonomous Internal Document QA and Policy Compliance* from my Agentic AI coursework. I adapted it for Google Colab and made these changes: OpenAI setup with keys kept in Colab Secrets, clear limits on each agent's role, a fixed routing-table format with deadlines set by severity, automatic chat termination, a summary built from each run's actual output, and `temperature: 0` for consistent results.
