# Multi-Agent Collaboration with LangGraph Using the A2A Protocol

## Overview

This project showcases **seamless multi-agent collaboration** across heterogeneous frameworks using the **Agent-to-Agent (A2A) Protocol** and **LangGraph**.

It orchestrates a workflow in which:

- A **LangChain ReAct agent** extracts the task from the user’s query.
- A **CrewAI agent** conducts web research based on the extracted task.
- A **custom OpenAI API agent** synthesizes the final response.
- **LangGraph** connects all agents within a stateful, modular execution graph.

---

## Problem Statement

### Business Need

Enterprises often rely on multiple AI agents optimized for specific functions—intent parsing, research, and content generation. These agents may be built with LangChain, CrewAI, or direct API calls. Coordinating them into a single, reliable pipeline is often complex, error-prone, and difficult to adapt.

### Objective

Design a flexible, modular system using the **A2A protocol** to:

- Enable agent interoperability,
- Maintain shared context,
- Support dynamic routing and collaboration among agents,
- Demonstrate plug-and-play capabilities across frameworks.

---

## Solution Approach

Use **LangGraph** to orchestrate the workflow:

1. **LangChain Agent (ReAct)**  
   Extracts the core task from user input.

2. **CrewAI Agent**  
   Executes simulated or real-time web research via a modular tool.

3. **Custom OpenAI API Agent**  
   Produces a complete, well-reasoned response based on gathered research.

4. **LangGraph**  
   Manages state transitions and context sharing in line with A2A principles.

---

## Architecture Diagram

```
[User Query]
     ↓
[LangChain Agent]
     ↓ (task extracted)
[CrewAI Agent]
     ↓ (web results)
[Custom OpenAI Agent]
     ↓ (final response)
  [Output to User]
```

---
