# Workflow

The application processes videos through a complete pipeline:

```mermaid
sequenceDiagram
    actor user as User
    participant cli as CLI
    participant service as Summarizer Service
    participant notion as Notion Client
    participant youtube as YouTube Client
    participant llm as LLM Client

    user->>cli: Execute with database ID
    cli->>service: Initialize with credentials
    cli->>service: Process videos from database
    service->>notion: Query video records
    notion-->>service: Return video URLs and metadata

    loop For each video
        service->>youtube: Fetch transcript and title
        youtube-->>service: Return transcript and title
        service->>llm: Generate summary
        llm-->>service: Return summary
        service->>llm: Extract main points
        llm-->>service: Return main points
        service->>notion: Update database with results
        notion-->>service: Confirm update
    end

    service-->>cli: Complete processing
    cli-->>user: Return summary of results
```

> **Note**: The CLI now includes enhanced error handling for unreachable LLM endpoints, providing specific connection error messages.
