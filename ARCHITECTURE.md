# RecoverAI System Architecture

The system follows a linear **"Ingest -> Smarten -> Execute -> Govern"** pipeline.

## High-Level Data Flow

1.  **Ingest (ERP -> Core):** Raw invoice data is pulled from the ERP.
2.  **Smarten (Core -> RISKON):** Data is scored using the ODE Model to determine `P(Recovery)`.
3.  **Execute (Core -> Portal):** Cases are routed to the SuRaksha Portal for agent action.
4.  **Govern (Portal -> Sentinel):** Interaction logs are analyzed in real-time for compliance risks.

## Diagram

```mermaid
graph TD
    subgraph FedEx_Environment [Strictly Controlled FedEx Environment]
        ERP[(FedEx ERP / Database)]
    end

    subgraph RecoverAI_Backend [FastAPI Microservices]
        AC[<b>Allocation Agent</b><br/><i>Routing Logic</i>]
        RE[<b>RISKON Engine</b><br/><i>Probabilistic Scoring</i>]
        Sen[<b>Sentinel Guard</b><br/><i>NLP Compliance</i>]
        
        ERP <==>|Raw Data| AC
        AC -->|Unscored| RE
        RE -->|Scored| AC
        AC ==>|Allocated Cases| Portal
        Portal -.->|Logs| Sen
    end

    subgraph DCA_Interface [Frontend]
        Portal(<b>SuRaksha Portal</b><br/><i>React Dashboard</i>)
    end
```
