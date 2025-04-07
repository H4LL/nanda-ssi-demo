# ACA‑Py Reactive MCP Server - A Decentralised Trust Layer for Inter-Agent Communications

## Overview

This project implements an interaction layer between an Aries Cloud Agent Python (ACA‑Py) and a generative AI environment instance using the MCP framework. We implement a reactive client which interacts with an ChatOllama model (Llama 3.2) and integrates multiple MCP tools generated from ACA‑Py’s swagger specification. The client supports multistage tool invocations with a structured conversation history and produces a clean, summarized output.

This project will run through the [alice-faber demo](https://github.com/openwallet-foundation/acapy/tree/main/docs/demo#the-alicefaber-python-demo) as hosted by the open wallet foundation. The twist is that alice and faber are both autonomous agents and they will be engaging in these flows autonomously.

### Phase 1: MCP Agents as an Interface between Credential Subjects and their Agent

Initially our goal is to be able to use MCP architecute to interact with our agents independently. The use case is that I am Faber, I want to issue a credential to Alice and I want to do so using the MCP client to interact with my agent on my behalf. We will also be using a seperate MCP client as Alice to interact with her Agent. Using these capabilities we will run through the alice-faber script:

1. Connect
2. Issue Credential
3. Prove Claim

###  Phase 2: MCP Agents as Credential Holders – Demonstrating Trust Attributes to Service Consumers

#### Use Case: Secure Access to a Restricted Resource

In this next phase, we leverage ACA‑Py to hold agent-driven credentials which manage reputation and trust assertions during nested inter-agent communications. For example, consider a scenario where one agent must prove its reputation and trustworthiness to gain access to a restricted resource managed by another agent.

**Benefits**

- **P2P Autonomous Trust Evaluations:**  
  Only agents that can prove their trustworthiness through valid credentials are allowed to access sensitive resources.

- **Interoperability:**  
  Standardized credentials and DIDComm protocols enable seamless interactions between diverse agents in a decentralized ecosystem.

- **Dynamic Trust Management:**  
  The system supports updates and revocations of credentials, ensuring that trust assertions remain current and reflective of an agent's ongoing reputation.

- **Credential-based Single-Use Access Tokens:**  
  Credentials can also function as single-use access tokens that grant temporary or limited access to computational or data resources. In environments where an AI is delegated resource access under budget constraints, these tokens help manage and monitor usage. Each token is authenticated, ensuring that only authorized and budget-compliant requests are processed.


**Agents Involved:**

- **Consumer Agent (Agent A):**  
  Represents an entity that wishes to access a restricted service or resource. This agent holds credentials attesting to its reputation, compliance, or other trust attributes issued by a trusted authority.

- **Service Provider Agent (Agent B):**  
  Manages access to the restricted resource and requires verification of the consumer agent's trust attributes before granting access.


## Summary

This use case demonstrates a complete agent-to-agent interaction where Agent A, acting as a credential holder, securely presents its trust attributes to Agent B, a service provider. Upon successful verification, Agent B grants access to a restricted resource, thereby ensuring that only trusted agents can participate in sensitive operations.

