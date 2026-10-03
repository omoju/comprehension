# Page: Overview

# Overview

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [CHANGELOG.md](CHANGELOG.md)
- [README.md](README.md)
- [docs/index.md](docs/index.md)
- [httpx/__version__.py](httpx/__version__.py)

</details>



HTTPX is an HTTP client library for Python 3.9+ that provides synchronous and asynchronous APIs with support for HTTP/1.1 and HTTP/2. The library implements a `requests`-compatible interface while adding modern features including async/await support, HTTP/2 protocol handling, and direct ASGI/WSGI application integration.

This page provides an architectural overview of the HTTPX library structure, core components, and processing flow.

## Purpose and Design Goals

HTTPX extends the `requests` library API with the following capabilities:

- **Dual API modes**: `httpx.Client` for synchronous operations, `httpx.AsyncClient` for asynchronous operations.
- **HTTP/2 protocol support**: Optional HTTP/2 implementation via the `h2` library.
- **Transport abstraction**: Pluggable transport layer supporting network HTTP, ASGI/WSGI direct calls, and mock transports.
- **Strict timeout defaults**: All network operations include timeout configuration by default.
- **Type annotations**: Complete type hints throughout the codebase.
- **Command-line interface**: Optional CLI tool via `httpx[cli]` installation.

The library delegates low-level HTTP protocol handling to the `httpcore` library, which manages connection pooling, HTTP/1.1 and HTTP/2 protocol implementation, and network I/O operations.

Sources: [README.md:16-17](), [README.md:59-71](), [httpx/__version__.py:1-3](), [docs/index.md:24](), [docs/index.md:66-74]()

## Architecture Overview

HTTPX Component Architecture

```mermaid
graph TB
    subgraph "API Layer - httpx/__init__.py"
        get["httpx.get()"]
        post["httpx.post()"]
        request["httpx.request()"]
        Client["httpx.Client"]
        AsyncClient["httpx.AsyncClient"]
    end
    
    subgraph "Client Implementation - httpx/_client.py"
        BaseClient["BaseClient"]
        ClientImpl["Client (sync)"]
        AsyncClientImpl["AsyncClient (async)"]
    end
    
    subgraph "Core Models - httpx/_models.py"
        Request["Request"]
        Response["Response"]
        Headers["Headers"]
        Cookies["Cookies"]
    end
    
    subgraph "URL Handling - httpx/_urls.py"
        URL["URL"]
        QueryParams["QueryParams"]
    end
    
    subgraph "Transport Layer - httpx/_transports/"
        BaseTransport["base.BaseTransport"]
        HTTPTransport["default.HTTPTransport"]
        AsyncHTTPTransport["default.AsyncHTTPTransport"]
        ASGITransport["asgi.ASGITransport"]
        WSGITransport["wsgi.WSGITransport"]
        MockTransport["mock.MockTransport"]
    end
    
    subgraph "Configuration - httpx/_config.py"
        Timeout["Timeout"]
        Limits["Limits"]
        Proxy["Proxy"]
    end
    
    subgraph "Authentication - httpx/_auth.py"
        Auth["Auth"]
        BasicAuth["BasicAuth"]
        DigestAuth["DigestAuth"]
        NetRCAuth["NetRCAuth"]
        FunctionAuth["FunctionAuth"]
    end
    
    subgraph "Content Processing"
        Decoders["httpx/_decoders.py<br/>ContentDecoder classes"]
        Multipart["httpx/_multipart.py<br/>MultipartStream"]
    end
    
    subgraph "External Dependencies"
        httpcore["httpcore library"]
        certifi["certifi library"]
        anyio["anyio library"]
    end
    
    get --> ClientImpl
    post --> ClientImpl
    request --> ClientImpl
    Client --> ClientImpl
    AsyncClient --> AsyncClientImpl
    
    ClientImpl --> BaseClient
    AsyncClientImpl --> BaseClient
    
    BaseClient --> Request
    BaseClient --> Response
    BaseClient --> URL
    BaseClient --> Timeout
    BaseClient --> Auth
    BaseClient --> BaseTransport
    
    BaseTransport --> HTTPTransport
    BaseTransport --> AsyncHTTPTransport
    BaseTransport --> ASGITransport
    BaseTransport --> WSGITransport
    BaseTransport --> MockTransport
    
    HTTPTransport --> httpcore
    AsyncHTTPTransport --> httpcore
    
    Response --> Decoders
    Request --> Multipart
    
    Timeout -.used by.- httpcore
    certifi -.used by.- httpcore
```

The architecture separates concerns into distinct layers:

1. **API Layer**: Top-level functions and client classes provide the public interface.
2. **Client Implementation**: `BaseClient` contains shared logic, with `Client` and `AsyncClient` subclasses for sync/async operations.
3. **Core Models**: `Request` and `Response` classes represent HTTP messages with associated headers, cookies, and content.
4. **Transport Abstraction**: `BaseTransport` interface enables pluggable implementations for network HTTP, ASGI/WSGI apps, and testing.
5. **Configuration System**: `Timeout`, `Limits`, and `Proxy` classes control client behavior.
6. **Content Processing**: Decoders handle compression (gzip, brotli, zstd), while multipart encoding handles file uploads.

For more details on the internal structure, see [Architecture Overview](#1.2).

Sources: [README.md:124-140](), [docs/index.md:107-123](), [CHANGELOG.md:15-15](), [CHANGELOG.md:59-60]()

## Installation and Dependencies

Install HTTPX via pip:

```shell
pip install httpx
```

Optional feature installations:

```shell
pip install httpx[http2]    # HTTP/2 support
pip install httpx[brotli]   # Brotli decompression
pip install httpx[zstd]     # Zstandard decompression
pip install httpx[socks]    # SOCKS proxy support
pip install httpx[cli]      # Command-line client
```

HTTPX requires Python 3.9 or higher. Support for Python 3.8 was dropped in version 0.28.0.

For a full breakdown of requirements and optional extras, see [Installation and Dependencies](#1.1).

Sources: [README.md:90-104](), [docs/index.md:129-148](), [CHANGELOG.md:11-11](), [CHANGELOG.md:59-60]()

## Request/Response Flow

Request Processing Pipeline with Code Entities

```mermaid
graph TB
    subgraph "Entry Point"
        user["User calls<br/>httpx.get(url)<br/>or client.get(url)"]
    end
    
    subgraph "httpx/_api.py"
        api_get["get()"]
        api_request["request()"]
    end
    
    subgraph "httpx/_client.py - Client Methods"
        client_get["Client.get()"]
        client_request["Client.request()"]
        build_request["Client.build_request()"]
    end
    
    subgraph "Request Construction"
        merge_url["_merge_url()"]
        merge_headers["_merge_headers()"]
        merge_cookies["_merge_cookies()"]
    end
    
    subgraph "Transport Selection"
        check_mounts["Check self._mounts dict<br/>for URL pattern match"]
        default_transport["Use self._transport"]
    end
    
    subgraph "httpx/_transports/"
        HTTPTransport_handle["HTTPTransport.handle_request()"]
        ASGITransport_handle["ASGITransport.handle_request()"]
        MockTransport_handle["MockTransport.handle_request()"]
    end
    
    subgraph "httpcore - Network I/O"
        httpcore_request["httpcore.request()"]
    end
    
    subgraph "Response Processing"
        Response_init["Response.__init__()"]
        decoder["ContentDecoder.decode()"]
    end
    
    subgraph "Return Path"
        response_return["Return Response object"]
    end
    
    user --> api_get
    api_get --> api_request
    api_request --> client_get
    client_get --> client_request
    client_request --> build_request
    
    build_request --> merge_url
    merge_url --> merge_headers
    merge_headers --> merge_cookies
    
    merge_cookies --> check_mounts
    check_mounts --> default_transport
    default_transport --> HTTPTransport_handle
    default_transport --> ASGITransport_handle
    default_transport --> MockTransport_handle
    
    HTTPTransport_handle --> httpcore_request
    
    httpcore_request --> Response_init
    ASGITransport_handle --> Response_init
    MockTransport_handle --> Response_init
    
    Response_init --> decoder
    decoder --> response_return
    response_return --> user
```

### Key Processing Steps

1. **Entry**: User calls top-level API functions like `httpx.get()` or instance methods on `httpx.Client`.
2. **Request Building**: `Client.build_request()` merges URL, headers, cookies, and applies authentication.
3. **Transport Selection**: The client selects the appropriate transport (e.g., `HTTPTransport`, `ASGITransport`) based on the URL and `mounts` configuration.
4. **Network Execution**: `Transport.handle_request()` delegates to `httpcore` for network I/O or handles the request directly (for ASGI/WSGI).
5. **Response Creation**: The `Response` object is initialized, wrapping the response stream.
6. **Stream Processing**: Content decoders handle decompression (gzip, brotli, zstd) transparently when content is accessed.

Sources: [README.md:28-39](), [docs/index.md:37-47](), [CHANGELOG.md:46-46](), [CHANGELOG.md:59-60]()

## Key Features

- **Standard Sync API**: A synchronous interface that follows the `requests` pattern.
- **Async Support**: Full `async/await` support for high-concurrency use cases.
- **HTTP/2**: Support for the HTTP/2 protocol, including multiplexed requests.
- **Direct App Calling**: Ability to call WSGI or ASGI applications directly for testing.
- **Strict Timeouts**: Timeouts are enabled by default to prevent hung requests.
- **Decompression**: Automatic handling of gzip, deflate, brotli, and zstd.

Sources: [README.md:59-89](), [docs/index.md:65-92](), [CHANGELOG.md:59-60]()

---

# Page: Installation and Dependencies

# Installation and Dependencies

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [docs/compatibility.md](docs/compatibility.md)
- [docs/quickstart.md](docs/quickstart.md)
- [pyproject.toml](pyproject.toml)
- [requirements.txt](requirements.txt)

</details>



This document covers how to install `httpx` and understand its dependency structure, including core requirements, optional features, and development dependencies. It also explains the relationship between `httpx` and its underlying transport library, `httpcore`.

## Overview

`httpx` follows a modular dependency approach with a minimal core and optional feature sets. The library requires Python 3.9+ and depends on several key packages for HTTP transport, SSL handling, and async support.

## Basic Installation

Install `httpx` using pip with the standard command:

```shell
pip install httpx
```

This installs `httpx` with its core dependencies, providing full HTTP/1.1 support, SSL verification, and both sync and async APIs.

Sources: [pyproject.toml:9-35](), [docs/quickstart.md:1-15]()

## Core Dependencies

`httpx` requires these essential packages that are automatically installed:

| Package | Version | Purpose |
|---------|---------|---------|
| `httpcore` | `1.*` | Low-level HTTP transport implementation |
| `certifi` | Latest | SSL certificate bundle for secure connections |
| `anyio` | Latest | Async library abstraction layer for compatibility with `asyncio` and `trio` |
| `idna` | Latest | Internationalized domain name support |

### The httpcore Relationship
The `httpcore` package provides the underlying transport layer. While `httpx` provides a high-level, developer-friendly API (Request/Response objects, Cookie management, etc.), `httpcore` handles the raw network socket communication and connection pooling.

Sources: [pyproject.toml:30-35](), [docs/compatibility.md:158-171]()

## Optional Dependencies

`httpx` provides several optional feature sets installed using extras syntax. These are defined in the `[project.optional-dependencies]` section of the project configuration.

### HTTP/2 Support
```shell
pip install httpx[http2]
```
Enables HTTP/2 protocol support through the `h2` package (versions 3-5).

### Command Line Interface
```shell
pip install httpx[cli]
```
Adds command-line client functionality. The CLI entry point is mapped to `httpx:main`.
- `click` (8.x): Command-line interface framework.
- `pygments` (2.x): Syntax highlighting for response output.
- `rich` (10-15): Rich terminal formatting and display.

### Compression Support
`httpx` supports standard `gzip` and `deflate` out of the box. Additional algorithms require:
```shell
pip install httpx[brotli]
pip install httpx[zstd]
```
- **Brotli**: Uses `brotli` on CPython or `brotlicffi` on other implementations.
- **Zstandard**: Uses `zstandard` (>=0.18.0).

### SOCKS Proxy Support
```shell
pip install httpx[socks]
```
Enables SOCKS proxy support through `socksio` (1.x).

Sources: [pyproject.toml:38-59](), [docs/quickstart.md:101-104]()

## Python Version Requirements

`httpx` requires **Python 3.9 or newer**. The project maintains a strict support policy for modern Python features.

Supported Python versions:
- Python 3.9 through 3.13

Sources: [pyproject.toml:9-27]()

## Development Dependencies

For development work, `httpx` uses additional tools defined in `requirements.txt`. These are pinned to specific versions to ensure environment stability for contributors.

### Documentation Tools
- `mkdocs` (1.6.1): Documentation site generator.
- `mkautodoc` (0.2.0): Automatic API documentation.
- `mkdocs-material` (9.6.18): Theme for documentation.

### Testing and Quality
- `pytest` (8.4.1): Testing framework.
- `coverage[toml]` (7.10.6): Code coverage analysis.
- `mypy` (1.17.1): Static type checking.
- `ruff` (0.12.11): Code linting and formatting.
- `trio` (0.31.0): Async concurrency library used for testing.

Sources: [requirements.txt:1-30]()

## Dependency Architecture

The following diagram illustrates the relationship between the `httpx` package, its core requirements, and the optional extras.

### Component Map: Package to Code Entities
```mermaid
graph TB
    subgraph "httpx_Package"
        httpx["httpx"]
        cli_main["httpx:main"]
    end
    
    subgraph "Core_Dependencies"
        httpcore["httpcore (v1.*)"]
        certifi["certifi"] 
        anyio["anyio"]
        idna["idna"]
    end
    
    subgraph "Optional_Extras"
        h2["h2 (HTTP/2)"]
        click["click (CLI)"]
        rich["rich (CLI UI)"]
        brotli["brotli / brotlicffi"]
        socksio["socksio (SOCKS)"]
        zstandard["zstandard (Zstd)"]
    end
    
    httpx --> httpcore
    httpx --> certifi
    httpx --> anyio
    httpx --> idna
    
    httpx -.->|"[http2]"| h2
    httpx -.->|"[cli]"| click
    httpx -.->|"[cli]"| rich
    cli_main -.-> click
    
    httpx -.->|"[brotli]"| brotli
    httpx -.->|"[socks]"| socksio
    httpx -.->|"[zstd]"| zstandard
```

Sources: [pyproject.toml:30-59](), [requirements.txt:5]()

## Installation Flow and Feature Enablement

This diagram shows how different installation commands enable specific code paths and features within the library.

### Logic Flow: Installation to Feature Set
```mermaid
graph TD
    subgraph "Installation_Commands"
        pip_basic["pip install httpx"]
        pip_full["pip install httpx[http2,cli,brotli,zstd,socks]"]
    end
    
    subgraph "Feature_Sets"
        core["Core HTTP/1.1<br/>(httpx.Client, httpx.AsyncClient)"]
        h2_feat["HTTP/2 Protocol<br/>(h2.H2Connection)"]
        cli_feat["CLI Tooling<br/>(httpx command)"]
        comp_feat["Advanced Decoding<br/>(BrotliDecoder, ZstdDecoder)"]
        proxy_feat["SOCKS Proxying<br/>(SOCKSProxy)"]
    end
    
    pip_basic --> core
    
    pip_full --> core
    pip_full --> h2_feat
    pip_full --> cli_feat
    pip_full --> comp_feat
    pip_full --> proxy_feat
```

Sources: [pyproject.toml:38-56](), [docs/quickstart.md:101-105]()

## Build System

`httpx` uses modern Python packaging standards with `hatchling` as the build backend.

### Build Configuration
- **Build system**: `hatchling` with `hatch-fancy-pypi-readme` for dynamic metadata.
- **Version source**: Defined in `httpx/__version__.py`.
- **Entry point**: The `httpx` command is registered via `project.scripts`.

### Package Structure
The source distribution includes:
- `/httpx`: Main package code.
- `/tests`: Comprehensive test suite.
- `/CHANGELOG.md`: Version history.

Sources: [pyproject.toml:1-59](), [pyproject.toml:70-76]()

## Development Installation

For development work, install `httpx` in editable mode with all extras to ensure the full test suite can run:

```shell
pip install -e .[brotli,cli,http2,socks,zstd]
```

This setup is used in the `requirements.txt` file to maintain a consistent environment for the core development team.

Sources: [requirements.txt:5]()

---

# Page: Architecture Overview

# Architecture Overview

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [CHANGELOG.md](CHANGELOG.md)
- [README.md](README.md)
- [httpx/__init__.py](httpx/__init__.py)
- [httpx/__version__.py](httpx/__version__.py)
- [httpx/_exceptions.py](httpx/_exceptions.py)

</details>



This document provides a high-level overview of httpx's modular architecture, showing how the core components work together to provide HTTP client functionality. It covers the main architectural layers, key abstractions, and the flow of requests through the system.

## System Architecture

httpx is built around a layered architecture that separates concerns between the public API, client management, transport abstraction, and configuration. The design allows for flexible customization while maintaining a clean separation between different responsibilities.

### Primary Architecture Layers

```mermaid
graph TD
    subgraph "Public API Layer"
        TopLevel["Top-Level Functions<br/>httpx.get(), httpx.post()"]
        ClientAPI["Client Classes<br/>Client, AsyncClient"]
        Models["Data Models<br/>Request, Response, URL, Headers"]
    end
    
    subgraph "Core Client System"
        BaseClient["BaseClient<br/>Shared Logic"]
        SyncClient["Client<br/>Synchronous Implementation"]
        AsyncClient["AsyncClient<br/>Asynchronous Implementation"]
    end
    
    subgraph "Transport Abstraction"
        BaseTransport["BaseTransport"]
        HTTPTransport["HTTPTransport<br/>Default HTTP/1.1 & HTTP/2"]
        ASGITransport["ASGITransport<br/>Direct ASGI Apps"]
        WSGITransport["WSGITransport<br/>Direct WSGI Apps"]
        MockTransport["MockTransport<br/>Testing"]
    end
    
    subgraph "Configuration & Processing"
        Config["Configuration Classes<br/>Timeout, Limits, Proxy"]
        Content["Content Processing<br/>Encoders, Decoders"]
        Auth["Authentication<br/>Auth implementations"]
    end
    
    subgraph "External Dependencies"
        HTTPCore["httpcore<br/>Connection Pooling"]
        AnyIO["anyio<br/>Async Abstraction"]
        Certifi["certifi<br/>SSL Certificates"]
    end
    
    TopLevel --> ClientAPI
    ClientAPI --> SyncClient
    ClientAPI --> AsyncClient
    SyncClient --> BaseClient
    AsyncClient --> BaseClient
    
    BaseClient --> BaseTransport
    BaseTransport --> HTTPTransport
    BaseTransport --> ASGITransport
    BaseTransport --> WSGITransport
    BaseTransport --> MockTransport
    
    BaseClient --> Config
    BaseClient --> Content
    BaseClient --> Auth
    BaseClient --> Models
    
    HTTPTransport --> HTTPCore
    AsyncClient --> AnyIO
    Config --> Certifi
```

Sources: [httpx/_client.py:1-54](), [httpx/_api.py:1-439](), [httpx/_models.py:1-51](), [httpx/_config.py:1-249](), [httpx/_transports/default.py:1-407]()

## Public API Layer

The public API provides two main entry points for making HTTP requests: top-level convenience functions and client instances.

### Top-Level Functions

The `httpx._api` module provides convenience functions like `get()`, `post()`, `put()`, etc. These functions create ephemeral `Client` instances internally:

| Function | Purpose | Implementation |
|----------|---------|----------------|
| `request()` | Generic HTTP request | Creates `Client` with specified config |
| `get()`, `post()`, etc. | HTTP method shortcuts | Call `request()` with method parameter |
| `stream()` | Streaming response | Uses `Client.stream()` context manager |

Sources: [httpx/_api.py:39-439]()

### Client Classes

The client system is built around three main classes:

```mermaid
graph TD
    BaseClient["BaseClient<br/>Abstract base class<br/>Shared configuration & logic"]
    Client["Client<br/>Synchronous HTTP client<br/>Thread-safe"]
    AsyncClient["AsyncClient<br/>Asynchronous HTTP client<br/>async/await support"]
    
    BaseClient --> Client
    BaseClient --> AsyncClient
    
    Client --> HTTPTransport["HTTPTransport<br/>Sync transport"]
    AsyncClient --> AsyncHTTPTransport["AsyncHTTPTransport<br/>Async transport"]
```

Sources: [httpx/_client.py:188-593](), [httpx/_client.py:594-1034]()

## Core Client System

### BaseClient

The `BaseClient` class contains shared logic for both synchronous and asynchronous clients:

- Configuration management (timeout, auth, headers, cookies)
- Request building via `build_request()`
- URL merging with `base_url`
- Header, cookie, and parameter merging
- Redirect handling logic

Key methods include:

| Method | Purpose |
|--------|---------|
| `build_request()` | Constructs `Request` objects with merged configuration |
| `_merge_url()` | Combines request URL with client `base_url` |
| `_merge_headers()` | Merges client and request headers |
| `_build_redirect_request()` | Creates redirect requests |

Sources: [httpx/_client.py:188-592]()

### Client State Management

Clients maintain state through the `ClientState` enum:

```python
class ClientState(enum.Enum):
    UNOPENED = 1  # Instantiated but not used
    OPENED = 2    # Within context manager or request sent  
    CLOSED = 3    # Explicitly closed or exited context
```

Sources: [httpx/_client.py:125-137]()

## Transport Abstraction

The transport layer provides a pluggable abstraction for sending HTTP requests. All transports implement either `BaseTransport` (sync) or `AsyncBaseTransport` (async).

### Transport Hierarchy

```mermaid
graph TD
    BaseTransport["BaseTransport<br/>Abstract sync transport"]
    AsyncBaseTransport["AsyncBaseTransport<br/>Abstract async transport"]
    
    HTTPTransport["HTTPTransport<br/>httpcore backend<br/>HTTP/1.1 & HTTP/2"]
    AsyncHTTPTransport["AsyncHTTPTransport<br/>httpcore backend<br/>HTTP/1.1 & HTTP/2"]
    
    WSGITransport["WSGITransport<br/>Direct WSGI app calls"]
    ASGITransport["ASGITransport<br/>Direct ASGI app calls"]
    MockTransport["MockTransport<br/>Handler function based"]
    
    BaseTransport --> HTTPTransport
    BaseTransport --> WSGITransport  
    BaseTransport --> MockTransport
    AsyncBaseTransport --> AsyncHTTPTransport
    AsyncBaseTransport --> ASGITransport
```

Sources: [httpx/_transports/default.py:135-407](), [httpx/_transports/base.py](), [httpx/__init__.py:33-99]()

### Transport Selection

Clients use URL pattern matching to select transports through the `_mounts` dictionary:

```mermaid
graph LR
    Request["Request with URL"] --> URLMatcher["URLPattern.matches()"]
    URLMatcher --> TransportSelection["Selected Transport"]
    
    Mounts["Client._mounts<br/>Dict[URLPattern, Transport]"] --> URLMatcher
```

The `_transport_for_url()` method iterates through mount patterns from most specific to least specific.

Sources: [httpx/_client.py:760-769]()

## Configuration System

Configuration in httpx is handled through dedicated classes that encapsulate related settings:

### Configuration Classes

| Class | Purpose | Key Properties |
|-------|---------|----------------|
| `Timeout` | Request timeout settings | `connect`, `read`, `write`, `pool` |
| `Limits` | Connection pool limits | `max_connections`, `max_keepalive_connections` |
| `Proxy` | Proxy server configuration | `url`, `auth`, `headers`, `ssl_context` |

Sources: [httpx/_config.py:72-248]()

### SSL Context Creation

The `create_ssl_context()` function handles SSL/TLS configuration. Note that in version 0.28.0+, the `verify` and `cert` string arguments are deprecated in favor of more constrained APIs.

```mermaid
graph TD
    verify["verify parameter"]
    cert["cert parameter"] 
    trust_env["trust_env parameter"]
    
    verify --> SSLContext["ssl.SSLContext"]
    cert --> SSLContext
    trust_env --> SSLContext
    
    SSLContext --> HTTPTransport["HTTPTransport._pool"]
```

Sources: [httpx/_config.py:23-70](), [CHANGELOG.md:21-35]()

## Data Models

The core data models represent HTTP concepts as Python objects:

### Request and Response Models

```mermaid
graph TD
    Request["Request<br/>method, url, headers<br/>content, stream"]
    Response["Response<br/>status_code, headers<br/>content, stream"]
    
    Headers["Headers<br/>Case-insensitive<br/>Multi-value support"]
    URL["URL<br/>Parsing & validation<br/>IDNA support"]
    Cookies["Cookies<br/>Cookie jar integration"]
    
    Request --> Headers
    Request --> URL
    Request --> Cookies
    Response --> Headers
    Response --> Cookies
```

Sources: [httpx/_models.py:382-514](), [httpx/_models.py:515-875](), [httpx/_models.py:139-380]()

## Request Processing Flow

The following diagram shows how a request flows through the httpx architecture:

```mermaid
graph TD
    UserCode["User Code<br/>client.get(url)"] --> BuildRequest["BaseClient.build_request()"]
    BuildRequest --> MergeConfig["Merge client/request config<br/>headers, params, cookies"]
    MergeConfig --> CreateRequest["Request object"]
    
    CreateRequest --> SendMethod["Client.send()"]
    SendMethod --> AuthFlow["Authentication flow<br/>Auth.sync_auth_flow()"]
    AuthFlow --> SelectTransport["_transport_for_url()"]
    
    SelectTransport --> HandleRequest["Transport.handle_request()"]
    HandleRequest --> HTTPCore["httpcore connection pool"]
    HTTPCore --> NetworkRequest["Network I/O"]
    
    NetworkRequest --> HTTPResponse["HTTP response"]
    HTTPResponse --> ResponseObject["Response object"]
    ResponseObject --> ContentDecoding["Content decoding<br/>gzip, brotli, zstd"]
    ContentDecoding --> UserCode
```

Sources: [httpx/_client.py:771-825](), [httpx/_client.py:879-929](), [httpx/_client.py:1001-1034](), [CHANGELOG.md:59-60]()

## Key Abstractions

### UseClientDefault Sentinel

The `USE_CLIENT_DEFAULT` sentinel allows distinguishing between "use client default" and "explicitly set to None":

```python
class UseClientDefault:
    """Indicates that client default should be used"""

USE_CLIENT_DEFAULT = UseClientDefault()
```

This enables proper parameter merging in methods like `request()`.

Sources: [httpx/_client.py:94-114]()

### Stream Binding

Response streams are bound to their response instances through `BoundSyncStream` and `BoundAsyncStream` classes. These ensure the `response.elapsed` property is set when the stream is closed.

Sources: [httpx/_client.py:139-183]()

### Exception Mapping

The transport layer maps `httpcore` exceptions to `httpx` exceptions through the `map_httpcore_exceptions()` context manager, providing a consistent exception hierarchy starting from `HTTPError`.

Sources: [httpx/_transports/default.py:95-119](), [httpx/_exceptions.py:1-32]()

This architecture provides a flexible, extensible foundation for HTTP client functionality while maintaining clear separation of concerns between different layers of the system.

---

# Page: Basic Usage

# Basic Usage

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [docs/compatibility.md](docs/compatibility.md)
- [docs/quickstart.md](docs/quickstart.md)
- [httpx/_api.py](httpx/_api.py)

</details>



This document provides a high-level overview of the primary patterns for making HTTP requests with `httpx`. It introduces the two main interfaces—top-level functions and client instances—and outlines how they relate to the library's configuration system.

For detailed implementation guides, see:
- [Making Requests](#2.1) — Specifics on HTTP methods, parameters, and payloads.
- [Working with Responses](#2.2) — Handling status codes, headers, and content decoding.
- [Authentication](#2.3) — Implementing Basic, Digest, and custom auth schemes.

## Request Patterns

HTTPX provides two primary ways to make HTTP requests: top-level functions for simple one-off requests, and client instances for more complex scenarios with shared configuration and connection pooling.

### Top-Level Functions

The simplest approach uses module-level functions defined in [httpx/_api.py:39-438](). These are ideal for quick scripts or isolated requests where connection reuse is not a priority.

```mermaid
graph TD
    subgraph "Top-Level API [httpx/_api.py]"
        get["httpx.get()"]
        post["httpx.post()"]  
        put["httpx.put()"]
        patch["httpx.patch()"]
        delete["httpx.delete()"]
        head["httpx.head()"]
        options["httpx.options()"]
        request["httpx.request()"]
        stream["httpx.stream()"]
    end
    
    subgraph "Internal Execution Flow"
        EphemeralClient["httpx.Client() instance"]
        ContextManager["with Client(...) as client"]
        ClientMethod["client.request()"]
    end
    
    subgraph "Result"
        Response["httpx.Response"]
    end
    
    get --> EphemeralClient
    post --> EphemeralClient
    request --> EphemeralClient
    stream --> EphemeralClient
    
    EphemeralClient --> ContextManager
    ContextManager --> ClientMethod
    ClientMethod --> Response
```

Each top-level function creates an ephemeral `Client` instance internally, makes the request, and ensures the client is closed after the response is returned [httpx/_api.py:102-120](). Note that functions for methods that do not traditionally support bodies (e.g., `get`, `head`) do not expose body-related parameters like `content`, `data`, or `json` [httpx/_api.py:174-243]().

### Client Instances

For persistent connections and shared state (like cookies or headers), use `Client` or `AsyncClient`. This is the equivalent of `requests.Session` [docs/compatibility.md:30-40]().

```mermaid
graph TD
    subgraph "Client Classes"
        SyncClient["httpx.Client"]
        AsyncClient["httpx.AsyncClient"]
    end
    
    subgraph "Shared State & Config"
        Headers["httpx.Headers"]
        Cookies["httpx.Cookies"]
        Timeout["httpx.Timeout"]
        Limits["httpx.Limits"]
    end
    
    subgraph "Methods"
        Request["client.request()"]
        Stream["client.stream()"]
    end
    
    Headers --> SyncClient
    Cookies --> SyncClient
    Timeout --> SyncClient
    
    SyncClient --> Request
    SyncClient --> Stream
    AsyncClient --> Request
```

Sources: [httpx/_api.py:102-120](), [httpx/_client.py:615-625](), [docs/compatibility.md:30-40]()

## Configuration and Defaults

HTTPX differs from other libraries by enforcing stricter defaults and providing granular configuration classes.

| Feature | HTTPX Behavior | Source |
|:---:|:---|:---|
| **Timeouts** | Enabled by default (5.0s). Set `timeout=None` to disable. | [docs/compatibility.md:149-157]() |
| **Redirects** | **Not** followed by default. Use `follow_redirects=True`. | [docs/compatibility.md:8-20]() |
| **HTTP/2** | Supported but must be explicitly enabled. | [docs/quickstart.md:465-470]() |
| **Binary Files** | Files for upload **must** be opened in binary mode. | [docs/compatibility.md:92-97]() |

### Core Configuration Entities

- **Timeouts**: Managed via `httpx.Timeout`. It provides granular control over `connect`, `read`, `write`, and `pool` phases [httpx/_config.py:72-157]().
- **Connection Limits**: Managed via `httpx.Limits`. Controls the maximum number of concurrent and keep-alive connections [httpx/_config.py:159-198]().
- **SSL**: Configured via the `verify` and `cert` parameters on the client, rather than per-request [docs/compatibility.md:172-177]().

Sources: [httpx/_config.py:72-198](), [docs/compatibility.md:8-157]()

## Summary of Usage Patterns

### Synchronous vs. Asynchronous
- Use `httpx.Client` for standard synchronous code [httpx/_client.py:615]().
- Use `httpx.AsyncClient` for `async/await` environments. All request methods on the async client are coroutines [docs/quickstart.md:480-495]().

### Request Data Handling
HTTPX distinguishes between different types of request bodies to avoid ambiguity:
- `data`: Used for form-encoded data [docs/compatibility.md:82-87]().
- `json`: Used for JSON-encoded payloads [docs/quickstart.md:227-249]().
- `content`: Used for raw binary or text content [docs/compatibility.md:72-80]().
- `files`: Used for multipart file uploads [docs/quickstart.md:172-188]().

### Streaming
Streaming is handled via the `.stream()` context manager. This ensures that the connection is properly closed and distinguishes between buffered and unbuffered I/O [docs/compatibility.md:129-147]().

Sources: [httpx/_api.py:123-172](), [docs/quickstart.md:1-260](), [docs/compatibility.md:70-147]()

---

# Page: Making Requests

# Making Requests

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_api.py](httpx/_api.py)
- [httpx/_client.py](httpx/_client.py)
- [tests/test_api.py](tests/test_api.py)
- [tests/test_config.py](tests/test_config.py)
- [tests/test_timeouts.py](tests/test_timeouts.py)

</details>



This page documents how to make HTTP requests using HTTPX's core API. It covers the top-level functions in `httpx/_api.py`, client methods, request parameters, and data encoding mechanisms.

## Request Methods Overview

HTTPX provides two primary approaches for making HTTP requests:

1. **Top-level API functions** - Simple functions that create ephemeral `Client` instances for one-off requests.
2. **Client instances** - Persistent objects with connection pooling and configuration management.

Both approaches ultimately use the same underlying request building and transport mechanisms but differ in connection lifecycle and performance characteristics.

**Request Processing Flow**

```mermaid
sequenceDiagram
    participant UserCode["User Code"]
    participant APIFunction["httpx.get()"]
    participant EphemeralClient["httpx.Client"]
    participant BuildRequest["_models.Request.build_request()"]
    participant HTTPTransport["_transports.default.HTTPTransport"]
    participant HTTPCore["httpcore.ConnectionPool"]
    
    UserCode->>APIFunction: "httpx.get(url, **kwargs)"
    APIFunction->>EphemeralClient: "Client(**config)"
    Note over EphemeralClient: "Context Manager __enter__"
    EphemeralClient->>BuildRequest: "build_request(method, url, **kwargs)"
    BuildRequest->>EphemeralClient: "Request object"
    EphemeralClient->>HTTPTransport: "handle_request(request)"
    HTTPTransport->>HTTPCore: "handle_request(req)"
    HTTPCore->>HTTPTransport: "httpcore.Response"
    HTTPTransport->>EphemeralClient: "httpx.Response"
    EphemeralClient->>UserCode: "Response"
    Note over EphemeralClient: "Context Manager __exit__ (Close)"
```

Sources:
- [httpx/_api.py:39-121]()
- [httpx/_api.py:174-207]()
- [httpx/_client.py:601-631]()

## Top-level API Functions

The [httpx/_api.py]() module provides convenience functions for each HTTP method. These functions are implemented as wrappers around the generic `request()` function:

| Method | Function | Body Parameters | Line Reference |
|--------|----------|-----------------|----------------|
| GET | `httpx.get()` | None (read-only) | [httpx/_api.py:174-207]() |
| POST | `httpx.post()` | `content`, `data`, `files`, `json` | [httpx/_api.py:282-320]() |
| PUT | `httpx.put()` | `content`, `data`, `files`, `json` | [httpx/_api.py:323-361]() |
| PATCH | `httpx.patch()` | `content`, `data`, `files`, `json` | [httpx/_api.py:364-402]() |
| DELETE | `httpx.delete()` | None (read-only) | [httpx/_api.py:405-438]() |
| HEAD | `httpx.head()` | None (read-only) | [httpx/_api.py:246-279]() |
| OPTIONS | `httpx.options()` | None (read-only) | [httpx/_api.py:210-243]() |

Each function creates a `Client` instance with the provided configuration, sends a single request via `client.request()`, and automatically closes the client using a context manager pattern [httpx/_api.py:102-120]().

**Generic request() Function**

The core `request()` function at [httpx/_api.py:39-121]() accepts all HTTP methods and provides the full parameter set:
- URL and query parameters (`params`)
- Request body (`content`, `data`, `files`, `json`)
- Headers and cookies
- Authentication, proxy, and timeout configuration
- SSL verification settings (`verify`)

Sources:
- [httpx/_api.py:39-438]()
- [tests/test_api.py:8-73]()

## Using Client Objects

For multiple requests, especially to the same host, you should use a `Client` or `AsyncClient` instance to benefit from connection pooling.

### Synchronous Client

The `httpx.Client` [httpx/_client.py:601]() is used for synchronous requests. It should ideally be used as a context manager to ensure connections are closed.

```python
with httpx.Client() as client:
    response = client.get('https://example.org')
```

### Asynchronous Client

The `httpx.AsyncClient` [httpx/_client.py:1388]() is used for `async/await` patterns.

```python
async with httpx.AsyncClient() as client:
    response = await client.get('https://example.org')
```

**Client Architecture and Transport Mapping**

```mermaid
graph TD
    subgraph "API Layer"
        TopLevelAPI["httpx._api.request"]
        ClientMethods["httpx.Client.get/post/..."]
        AsyncClientMethods["httpx.AsyncClient.get/post/..."]
    end
    
    subgraph "Client Classes"
        Client["httpx.Client"]
        AsyncClient["httpx.AsyncClient"]
    end
    
    subgraph "Transport Implementation"
        HTTPTransport["httpx._transports.default.HTTPTransport"]
        AsyncHTTPTransport["httpx._transports.default.AsyncHTTPTransport"]
    end
    
    TopLevelAPI -->|"Instantiates"| Client
    ClientMethods --> Client
    AsyncClientMethods --> AsyncClient
    
    Client -->|"calls"| HTTPTransport
    AsyncClient -->|"calls"| AsyncHTTPTransport
```

Sources:
- [httpx/_client.py:601-1385]()
- [httpx/_client.py:1388-2121]()

## Request Parameters

All request functions and client methods accept parameters defined by the type aliases in [httpx/_types.py]().

### URL and Query Parameters

- **URL Types**: Accepts `httpx.URL` or `str` [httpx/_types.py:33]().
- **Query Parameter Types**: `QueryParamTypes` [httpx/_types.py:40]() supports `QueryParams`, dictionaries, or sequences of tuples.

### Headers and Cookies

- **Header Types**: `HeaderTypes` [httpx/_types.py:38]() accepts `Headers` objects (case-insensitive), dictionaries, or sequences of tuples.
- **Cookie Types**: `CookieTypes` [httpx/_types.py:37]() supports `Cookies` objects, dictionaries, or sequences of tuples.

### Timeout Configuration

HTTPX uses a default timeout of 5 seconds [httpx/_config.py:17]().
- **Timeout Types**: `TimeoutTypes` [httpx/_types.py:46]() accepts float, `None` (no timeout), or `httpx.Timeout` objects [httpx/_config.py:72]().
- Granular timeouts can be set for `connect`, `read`, `write`, and `pool` [httpx/_config.py:75-79]().

Sources:
- [httpx/_types.py:33-47]()
- [httpx/_config.py:72-157]()
- [tests/test_timeouts.py:7-56]()

## Sending Request Data

HTTPX processes request body data based on the parameter used:

### Content Encoding Priority

1. **`json`**: Encoded as JSON with `application/json` Content-Type [httpx/_api.py:47]().
2. **`files`**: Encoded as `multipart/form-data` [httpx/_api.py:46]().
3. **`data`**: Encoded as `application/x-www-form-urlencoded` [httpx/_api.py:45]().
4. **`content`**: Raw bytes or byte iterator [httpx/_api.py:44]().

### Raw Content Handling

The `content` parameter allows sending raw bytes, strings (UTF-8 encoded), or iterables for streaming uploads [tests/test_api.py:17-43]().

**Request Body Processing Pipeline**

```mermaid
graph LR
    subgraph "Input Parameters"
        JSONParam["json"]
        FilesParam["files"]  
        DataParam["data"]
        ContentParam["content"]
    end
    
    subgraph "Encoders"
        JSONEnc["JSON"]
        MultiEnc["Multipart"]
        FormEnc["URL-Encoded"]
    end
    
    JSONParam --> JSONEnc
    FilesParam --> MultiEnc
    DataParam --> FormEnc
    ContentParam -->|"Raw/Stream"| FinalStream["Byte Stream"]
    
    JSONEnc --> FinalStream
    MultiEnc --> FinalStream
    FormEnc --> FinalStream
```

Sources:
- [httpx/_api.py:39-56]()
- [httpx/_types.py:41-44]()

## Handling Redirects

By default, HTTPX does **not** follow redirects [httpx/_client.py:197](). To enable them, set `follow_redirects=True`.

```python
response = httpx.get('https://example.org', follow_redirects=True)
```

The client tracks redirect history in `response.history` [httpx/_models.py]().

Sources:
- [httpx/_client.py:197-198]()
- [httpx/_api.py:53]()

## Streaming Responses

For large responses, use the `stream()` context manager [httpx/_api.py:124-172](). This prevents the entire response body from being loaded into memory at once.

```python
with httpx.stream("GET", "https://example.org") as response:
    for chunk in response.iter_bytes():
        process(chunk)
```

Sources:
- [httpx/_api.py:124-172]()
- [tests/test_api.py:75-83]()

## Error Handling

HTTPX raises specific exceptions for different failure modes:
- `httpx.ConnectTimeout`: Failed to establish a connection [tests/test_timeouts.py:31]().
- `httpx.ReadTimeout`: Failed to read data within the timeout [tests/test_timeouts.py:11]().
- `httpx.WriteTimeout`: Failed to write data within the timeout [tests/test_timeouts.py:20]().
- `httpx.PoolTimeout`: Failed to acquire a connection from the pool [tests/test_timeouts.py:42]().

Sources:
- [httpx/_exceptions.py]()
- [tests/test_timeouts.py:1-56]()

---

# Page: Working with Responses

# Working with Responses

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_models.py](httpx/_models.py)
- [httpx/_status_codes.py](httpx/_status_codes.py)
- [tests/models/test_requests.py](tests/models/test_requests.py)
- [tests/models/test_responses.py](tests/models/test_responses.py)
- [tests/test_status_codes.py](tests/test_status_codes.py)

</details>



This page covers basic patterns for accessing and working with HTTP response data in HTTPX, including status codes, headers, and various content access methods. For streaming responses, see [Streaming](#3.5). For comprehensive Response class documentation, see [Response Objects](#4.2). For details on content encoding and decompression, see [Content Encoding and Decoding](#4.6).

## Response Object Structure

When HTTPX completes an HTTP request, it returns a `Response` object defined in `httpx._models.Response`. This object provides multiple interfaces for accessing the response data depending on your needs.

```mermaid
graph TB
    subgraph "httpx._models.Response"
        Response["Response"]
        
        subgraph "Status Information"
            status_code["status_code: int"]
            reason_phrase["reason_phrase: str"]
            is_success["is_success: bool"]
            is_error["is_error: bool"]
            is_redirect["is_redirect: bool"]
        end
        
        subgraph "Content Access"
            content["content: bytes"]
            text["text: str"]
            json["json()"]
            encoding["encoding: str"]
        end
        
        subgraph "Metadata"
            headers["headers: Headers"]
            cookies["cookies: Cookies"]
            url["url: URL"]
            elapsed["elapsed: timedelta"]
        end
        
        subgraph "State Properties"
            is_closed["is_closed: bool"]
            is_stream_consumed["is_stream_consumed: bool"]
        end
    end
    
    Response --> status_code
    Response --> reason_phrase
    Response --> is_success
    Response --> is_error
    Response --> is_redirect
    Response --> content
    Response --> text
    Response --> json
    Response --> encoding
    Response --> headers
    Response --> cookies
    Response --> url
    Response --> elapsed
    Response --> is_closed
    Response --> is_stream_consumed
```

**Diagram: Response Object Properties and Methods**

Sources: [httpx/_models.py:596-618](), [tests/models/test_responses.py:31-43]()

## Status Codes and Validation

### Accessing Status Codes

The `status_code` property returns the HTTP status code as an integer [httpx/_models.py:656-658](). The `reason_phrase` property provides the corresponding text description, retrieved from the `codes` enum [httpx/_models.py:660-665]().

```python
response.status_code  # 200
response.reason_phrase  # "OK"
```

Status codes can be checked against named constants from `httpx.codes`, which is an `IntEnum` [httpx/_status_codes.py:8-26]():

```python
response.status_code == httpx.codes.OK  # True for 200
response.status_code == httpx.codes.NOT_FOUND  # True for 404
```

Sources: [httpx/_models.py:656-665](), [httpx/_status_codes.py:8-26](), [tests/models/test_responses.py:31-43]()

### Response State Properties

HTTPX provides boolean properties to categorize responses by status code ranges, implemented via the `codes` helper class [httpx/_status_codes.py:46-85]():

| Property | Status Range | Description |
|----------|--------------|-------------|
| `is_informational` | 1xx | Informational responses [httpx/_models.py:667-669]() |
| `is_success` | 2xx | Successful responses [httpx/_models.py:671-673]() |
| `is_redirect` | 3xx | Redirection responses [httpx/_models.py:675-677]() |
| `is_client_error` | 4xx | Client error responses [httpx/_models.py:679-681]() |
| `is_server_error` | 5xx | Server error responses [httpx/_models.py:683-685]() |
| `is_error` | 4xx or 5xx | Any error response [httpx/_models.py:687-689]() |

Sources: [httpx/_models.py:667-689](), [httpx/_status_codes.py:46-85](), [tests/models/test_responses.py:91-147]()

### Raising Exceptions for Error Responses

The `raise_for_status()` method checks if the response status code indicates an error and raises `httpx.HTTPStatusError` if so [httpx/_models.py:737-767](). HTTPX raises exceptions for **all non-2xx responses**, including 1xx informational and 3xx redirect codes.

```python
response.raise_for_status()  # Raises HTTPStatusError for non-2xx
```

The exception includes both `.request` and `.response` attributes, and requires the response to have a request instance associated with it, otherwise it raises a `RuntimeError` [httpx/_models.py:739-741]().

Sources: [httpx/_models.py:737-767](), [tests/models/test_responses.py:91-147]()

## Response Headers

Response headers are accessible through the `headers` property, which returns a `httpx.Headers` object [httpx/_models.py:717-719](). This class is a case-insensitive multi-dict [httpx/_models.py:139-142]().

```python
response.headers['content-type']  # Case-insensitive access
response.headers.get('Content-Type')  # Also case-insensitive
```

Multiple values for the same header field are combined into a single comma-separated value during string access [httpx/_models.py:206-214]().

Sources: [httpx/_models.py:139-142](), [httpx/_models.py:206-214](), [httpx/_models.py:717-719]()

## Response Content Access

HTTPX provides three primary methods for accessing response content, processing bytes through a pipeline of decoders.

```mermaid
graph LR
    subgraph "Content Access Flow"
        RawBytes["Raw Response Bytes"]
        
        subgraph "httpx._decoders"
            Decoder["MultiDecoder"]
            gzip["GZipDecoder"]
            deflate["DeflateDecoder"]
            brotli["BrotliDecoder"]
            zstd["ZStandardDecoder"]
        end
        
        subgraph "httpx._models.Response"
            content[".content"]
            text[".text"]
            json_method[".json()"]
        end
    end
    
    RawBytes --> Decoder
    Decoder --> gzip
    Decoder --> deflate
    Decoder --> brotli
    Decoder --> zstd
    
    gzip --> content
    deflate --> content
    brotli --> content
    zstd --> content
    
    content --> text
    text --> json_method
```

**Diagram: Response Content Processing Pipeline**

Sources: [httpx/_decoders.py:333-365](), [httpx/_models.py:793-861]()

### Binary Content

The `.content` property returns the response body as raw bytes [httpx/_models.py:793-802](). If the response was streamed, it must be read first via `.read()` or `.aread()`, otherwise a `ResponseNotRead` exception is raised [httpx/_models.py:797-798]().

```python
response.content  # b'<!doctype html>...'
```

Sources: [httpx/_models.py:793-802](), [tests/models/test_responses.py:46-53]()

### Text Content

The `.text` property returns the response body decoded as a Unicode string [httpx/_models.py:804-814](). It uses the `encoding` property to perform the decoding.

```python
response.text  # '<!doctype html>...'
response.encoding  # 'utf-8'
```

Sources: [httpx/_models.py:804-814](), [tests/models/test_responses.py:55-65]()

### JSON Content

The `.json()` method decodes the response body as JSON using the standard `json` library [httpx/_models.py:847-861]().

```python
response.json()  # {'key': 'value'}
```

Sources: [httpx/_models.py:847-861](), [tests/models/test_responses.py:79-89]()

## Character Encoding

### Encoding Detection Priority

HTTPX determines text encoding using the following logic in the `encoding` property [httpx/_models.py:816-841]():
1. Use the `_encoding` attribute if it has been set explicitly.
2. Use the `charset` from the `Content-Type` header [httpx/_models.py:85-91]().
3. Use a `default_encoding` callable if provided during initialization.
4. Fall back to "utf-8".

Sources: [httpx/_models.py:85-91](), [httpx/_models.py:816-841](), [tests/models/test_responses.py:157-273]()

## Content Decompression

HTTPX handles content decompression automatically in the `decoder` property [httpx/_models.py:774-791](). It uses `httpx._decoders.MultiDecoder` to wrap the response stream [httpx/_decoders.py:333-365]().

| Encoding | Decoder Class |
|----------|---------------|
| `gzip` | `GZipDecoder` [httpx/_decoders.py:171-193]() |
| `deflate` | `DeflateDecoder` [httpx/_decoders.py:196-214]() |
| `br` | `BrotliDecoder` [httpx/_decoders.py:217-240]() |
| `zstd` | `ZStandardDecoder` [httpx/_decoders.py:243-266]() |

Sources: [httpx/_decoders.py:171-266](), [httpx/_models.py:774-791]()

## Response Metadata

### Request Reference

The `request` property returns the `httpx.Request` instance that triggered this response [httpx/_models.py:643-654]().

```python
response.request.method  # 'GET'
```

Sources: [httpx/_models.py:643-654](), [tests/models/test_responses.py:925-939]()

### Cookies

The `cookies` property returns a `httpx.Cookies` instance containing cookies from `Set-Cookie` headers [httpx/_models.py:725-731]().

Sources: [httpx/_models.py:725-731](), [httpx/_models.py:356-363]()

### Timing and State

*   **`elapsed`**: The time taken from sending the request to receiving the response headers [httpx/_models.py:733-735]().
*   **`is_closed`**: `True` if the response stream has been closed [httpx/_models.py:916-918]().
*   **`is_stream_consumed`**: `True` if the response body has been fully read [httpx/_models.py:920-922]().

Sources: [httpx/_models.py:733-735](), [httpx/_models.py:916-922]()

---

# Page: Authentication

# Authentication

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [docs/advanced/authentication.md](docs/advanced/authentication.md)
- [docs/advanced/event-hooks.md](docs/advanced/event-hooks.md)
- [docs/advanced/resource-limits.md](docs/advanced/resource-limits.md)
- [docs/advanced/text-encodings.md](docs/advanced/text-encodings.md)
- [docs/advanced/timeouts.md](docs/advanced/timeouts.md)
- [httpx/_auth.py](httpx/_auth.py)
- [tests/client/test_auth.py](tests/client/test_auth.py)
- [tests/test_auth.py](tests/test_auth.py)

</details>



## Purpose and Scope

This page documents HTTPX's authentication system, which provides built-in support for HTTP authentication schemes and a flexible framework for implementing custom authentication. HTTPX includes three pre-built authentication classes (`BasicAuth`, `DigestAuth`, `NetRCAuth`) and a generator-based protocol for implementing custom multi-step authentication flows.

For information about SSL client certificates, see [SSL and Security](#6.3). For information about proxy authentication, see [Proxy Support](#5.3).

## Architecture Overview

HTTPX authentication is built on a generator-based protocol that allows authentication schemes to inspect responses and make multiple requests as needed. This design supports complex authentication flows like OAuth token refresh, digest authentication challenges, and other multi-step protocols.

### Authentication Flow Integration

```mermaid
flowchart TD
    BuildRequest["Client.build_request()"]
    ApplyAuth["Apply Auth"]
    SendRequest["Transport.handle_request()"]
    ReceiveResponse["Receive Response"]
    CheckAuth{"Auth needs<br/>another request?"}
    ReturnResponse["Return Response to User"]
    
    BuildRequest --> ApplyAuth
    ApplyAuth --> SendRequest
    SendRequest --> ReceiveResponse
    ReceiveResponse --> CheckAuth
    CheckAuth -->|"Yes (yield request)"| ApplyAuth
    CheckAuth -->|"No (generator ends)"| ReturnResponse
    
    note1["Auth generator can:<br/>- Inspect response<br/>- Modify request<br/>- Yield new request"]
    CheckAuth -.-> note1
```

**Authentication Flow in Request Processing**

The authentication system integrates into the request processing pipeline at the point where the client builds and sends requests. The auth flow generator can yield multiple requests, inspect responses, and decide whether to continue the authentication sequence.

Sources: [httpx/_auth.py:22-111](), [tests/client/test_auth.py:87-113]()

### Core Components

```mermaid
graph TB
    subgraph "Auth Base Classes"
        Auth["Auth<br/>(base class)"]
        FunctionAuth["FunctionAuth<br/>(callable wrapper)"]
    end
    
    subgraph "Built-in Implementations"
        BasicAuth["BasicAuth<br/>username + password"]
        DigestAuth["DigestAuth<br/>challenge-response"]
        NetRCAuth["NetRCAuth<br/>.netrc file lookup"]
    end
    
    subgraph "Generator Methods"
        AuthFlow["auth_flow()<br/>(base implementation)"]
        SyncAuthFlow["sync_auth_flow()<br/>(sync I/O)"]
        AsyncAuthFlow["async_auth_flow()<br/>(async I/O)"]
    end
    
    subgraph "Client Integration"
        ClientBuild["Client.build_request()"]
        ClientSend["Client.send()"]
        Transport["Transport.handle_request()"]
    end
    
    Auth --> FunctionAuth
    Auth --> BasicAuth
    Auth --> DigestAuth
    Auth --> NetRCAuth
    
    Auth --> AuthFlow
    Auth --> SyncAuthFlow
    Auth --> AsyncAuthFlow
    
    ClientBuild -.applies.-> Auth
    ClientSend -.uses.-> SyncAuthFlow
    ClientSend -.uses.-> AsyncAuthFlow
    SyncAuthFlow -.sends via.-> Transport
```

**Authentication Component Architecture**

The `Auth` base class defines the authentication interface with three generator methods for different execution contexts. Built-in implementations extend this base class, and client code applies authentication during request building.

Sources: [httpx/_auth.py:22-111](), [httpx/_auth.py:113-173]()

## Built-in Authentication Schemes

### BasicAuth

HTTP Basic Authentication sends credentials in the `Authorization` header using Base64 encoding. Credentials are sent with every request.

**Usage:**

```python
# As a tuple (converted to BasicAuth automatically)
auth = ("username", "password")

# Explicit BasicAuth instance
auth = httpx.BasicAuth("username", "password")

# In requests
response = httpx.get("https://example.com", auth=auth)

# On client
client = httpx.Client(auth=auth)
```

**Implementation Details:**

The `BasicAuth` class builds an `Authorization` header in the format `Basic <base64(username:password)>`. The authentication happens immediately on the first request with no challenge-response flow.

| Property | Value |
|----------|-------|
| Class | `httpx.BasicAuth` |
| Header Format | `Basic <base64-credentials>` |
| Requires Challenge | No |
| Multi-step Flow | No |
| File Location | [httpx/_auth.py:126-143]() |

**BasicAuth Flow:**

```mermaid
sequenceDiagram
    participant Client
    participant BasicAuth
    participant Server
    
    Client->>BasicAuth: Pass request
    BasicAuth->>BasicAuth: Add Authorization header
    BasicAuth->>Server: Send request with auth
    Server->>BasicAuth: Return response
    BasicAuth->>Client: Return response
    
    Note over BasicAuth,Server: No challenge required<br/>Auth sent immediately
```

Sources: [httpx/_auth.py:126-143](), [tests/client/test_auth.py:163-173](), [tests/test_auth.py:14-27]()

### DigestAuth

HTTP Digest Authentication is a challenge-response authentication scheme. Unlike basic authentication, it provides protection against password sniffing by using hashes and can be used over unencrypted `http` connections. It requires an additional round-trip to negotiate the authentication.

**Usage:**

```python
auth = httpx.DigestAuth("username", "password")

# Make request - first attempt returns 401 with challenge
response = httpx.get("https://example.com", auth=auth)

# DigestAuth automatically handles the challenge and retries
```

**Digest Authentication Flow:**

```mermaid
sequenceDiagram
    participant Client
    participant DigestAuth
    participant Server
    
    Client->>DigestAuth: Initial request
    DigestAuth->>Server: Request (no auth header)
    Server->>DigestAuth: 401 + WWW-Authenticate challenge
    DigestAuth->>DigestAuth: Parse challenge<br/>Store in _last_challenge<br/>Compute response hash
    DigestAuth->>Server: Request with Authorization header
    Server->>DigestAuth: 200 OK
    DigestAuth->>Client: Return final response
    
    Note over DigestAuth: Subsequent requests use<br/>cached challenge + incremented<br/>nonce count
```

**Challenge Caching and Nonce Count:**

`DigestAuth` maintains state across multiple requests to avoid unnecessary authentication roundtrips:

- `_last_challenge`: Stores the most recent server challenge [httpx/_auth.py:190]()
- `_nonce_count`: Increments with each request (sent as `nc` parameter) [httpx/_auth.py:191]()

If a subsequent request receives a 401 response, the challenge and nonce count are reset.

| Property | Value |
|----------|-------|
| Class | `httpx.DigestAuth` |
| Header Format | `Digest username="...", realm="...", nonce="...", uri="...", response="...", ...` |
| Requires Challenge | Yes (401 with WWW-Authenticate) |
| Multi-step Flow | Yes (initial request + retry with hash) |
| Supported Algorithms | MD5, MD5-SESS, SHA, SHA-SESS, SHA-256, SHA-256-SESS, SHA-512, SHA-512-SESS |
| File Location | [httpx/_auth.py:175-341]() |

**Digest Parameters:**

The digest response hash is computed from:
- Username and password [httpx/_auth.py:188-189]()
- Server's realm and nonce
- Request method and URI
- Client nonce (cnonce) and nonce count (nc)
- Quality of protection (qop) - only "auth" is supported

Sources: [httpx/_auth.py:175-341](), [tests/client/test_auth.py:413-457](), [tests/test_auth.py:44-67](), [docs/advanced/authentication.md:29-41]()

### NetRCAuth

`NetRCAuth` reads credentials from a `.netrc` file, which associates authentication credentials with specified hosts. When a request is made to a host found in the file, the username and password are included using HTTP basic authentication.

**Usage:**

```python
# Use default .netrc location (~/.netrc)
auth = httpx.NetRCAuth()

# Specify custom netrc file
auth = httpx.NetRCAuth(file="/path/to/.netrc")

client = httpx.Client(auth=auth)
```

**NetRC File Format:**

```
machine example.org
login username
password secret123

machine api.example.com
login apiuser
password apikey456
```

**Behavior:**

- Looks up credentials based on request URL host [httpx/_auth.py:158]()
- If credentials found: adds Basic Authentication header [httpx/_auth.py:164-167]()
- If credentials not found: sends request without authentication [httpx/_auth.py:161]()
- Falls back gracefully when no match exists

| Property | Value |
|----------|-------|
| Class | `httpx.NetRCAuth` |
| File Format | Standard Unix .netrc |
| Default Location | `~/.netrc` |
| Authentication Type | Basic Auth (after lookup) |
| File Location | [httpx/_auth.py:145-173]() |

Sources: [httpx/_auth.py:145-173](), [tests/client/test_auth.py:237-271](), [docs/advanced/authentication.md:43-85]()

## Using Authentication

### Passing Authentication to Requests

Authentication can be passed to individual request functions:

```python
# Tuple automatically converted to BasicAuth
httpx.get("https://example.com", auth=("user", "pass"))

# Explicit auth instance
auth = httpx.DigestAuth("user", "pass")
httpx.post("https://example.com/api", auth=auth)

# Custom callable
def custom_auth(request):
    request.headers["Authorization"] = "Bearer token123"
    return request

httpx.get("https://example.com", auth=custom_auth)
```

Sources: [docs/advanced/authentication.md:1-7](), [tests/client/test_auth.py:222-235]()

### Passing Authentication to Clients

Authentication can be configured at the client level to apply to all requests:

```python
# All requests from this client will use auth
client = httpx.Client(auth=("user", "pass"))
client.get("https://example.com")
client.post("https://example.com/data")
```

**Client vs Request-Level Auth:**

```mermaid
graph LR
    subgraph "Client-Level Auth"
        ClientAuth["client = httpx.Client(auth=...)"]
        Req1["client.get(url)"]
        Req2["client.post(url)"]
        ClientAuth --> Req1
        ClientAuth --> Req2
    end
    
    subgraph "Request-Level Auth"
        NoClientAuth["client = httpx.Client()"]
        ReqAuth1["client.get(url, auth=...)"]
        ReqAuth2["client.post(url, auth=...)"]
        NoClientAuth -.-> ReqAuth1
        NoClientAuth -.-> ReqAuth2
    end
    
    Note1["Auth applies to all<br/>requests automatically"]
    Note2["Auth specified per<br/>request as needed"]
    
    ClientAuth -.-> Note1
    ReqAuth1 -.-> Note2
```

Sources: [tests/client/test_auth.py:207-219](), [tests/client/test_auth.py:323-336](), [docs/advanced/authentication.md:9-15]()

### Disabling Client-Level Authentication

A client configured with authentication can have auth disabled for specific requests by passing `auth=None`:

```python
client = httpx.Client(auth=("user", "pass"))

# Uses client auth
response = client.get("https://api.example.com/data")

# Disables auth for this request
response = client.get("https://example.com/public", auth=None)
```

Sources: [tests/client/test_auth.py:289-301]()

### Authentication with Streaming Requests

Authentication works with streaming requests. Note that some auth schemes (like Digest) require access to the request or response body, which may affect streaming capabilities.

```python
auth = httpx.BasicAuth("user", "pass")

async with httpx.AsyncClient(auth=auth) as client:
    async with client.stream("GET", "https://example.com") as response:
        # response.aread() might be needed if auth requires body
        await response.aread() 
```

Sources: [tests/client/test_auth.py:176-192]()

### Authentication in URLs

Basic authentication credentials can be embedded in URLs:

```python
response = httpx.get("https://user:password@example.com/")
# Equivalent to: httpx.get("https://example.com/", auth=("user", "password"))
```

The credentials are automatically extracted and used for Basic Authentication. For security, the password is hidden in URL representations.

Sources: [tests/client/test_auth.py:195-204](), [tests/client/test_auth.py:303-308]()

## Custom Authentication

### Implementing the Auth Protocol

Custom authentication schemes are implemented by subclassing `Auth` and overriding `auth_flow()`:

```mermaid
flowchart TD
    SubclassAuth["Subclass httpx.Auth"]
    OverrideFlow["Override auth_flow()"]
    YieldRequest["Yield modified request"]
    InspectResponse["response = yield request"]
    DecideNext{"Need another<br/>request?"}
    YieldAgain["Yield another request"]
    EndFlow["Return (end generator)"]
    
    SubclassAuth --> OverrideFlow
    OverrideFlow --> YieldRequest
    YieldRequest --> InspectResponse
    InspectResponse --> DecideNext
    DecideNext -->|Yes| YieldAgain
    DecideNext -->|No| EndFlow
    YieldAgain --> InspectResponse
```

**Custom Auth Implementation Pattern**

Sources: [httpx/_auth.py:22-61](), [docs/advanced/authentication.md:87-107]()

### Generator Protocol

The authentication flow is implemented as a generator that yields requests and receives responses:

```python
class CustomAuth(httpx.Auth):
    def auth_flow(self, request):
        # Modify request
        request.headers["X-Custom-Auth"] = "initial"
        
        # Send request and get response
        response = yield request
        
        # Inspect response and decide if another request is needed
        if response.status_code == 401:
            token = response.headers["X-Auth-Token"]
            request.headers["X-Custom-Auth"] = f"token-{token}"
            
            # Send another request
            yield request
```

**Key Points:**

- `yield request` sends the request and pauses the generator [httpx/_auth.py:42-45]()
- Client sends the response back into the generator via `.send(response)` [httpx/_auth.py:48-53]()
- Generator can yield multiple requests [httpx/_auth.py:58]()
- Returning or reaching the end returns the last response to the user [httpx/_auth.py:55-56]()

Sources: [httpx/_auth.py:38-61](), [tests/client/test_auth.py:87-113](), [docs/advanced/authentication.md:109-123]()

### Sync vs Async Authentication

For authentication schemes that perform I/O (disk/network) or use concurrency primitives (locks), separate sync and async implementations should be provided:

```python
class SyncOrAsyncAuth(httpx.Auth):
    def __init__(self):
        self._lock = threading.Lock()
        self._async_lock = anyio.Lock()
    
    def sync_auth_flow(self, request):
        with self._lock:
            request.headers["Authorization"] = "sync-auth"
        yield request
    
    async def async_auth_flow(self, request):
        async with self._async_lock:
            request.headers["Authorization"] = "async-auth"
        yield request
```

**When to Override:**

| Method | Override When |
|--------|---------------|
| `auth_flow()` | Pure logic, no I/O or locks [httpx/_auth.py:26-28]() |
| `sync_auth_flow()` | Need file I/O, network calls, or threading primitives [httpx/_auth.py:29-33]() |
| `async_auth_flow()` | Need async I/O or async locks [httpx/_auth.py:29-33]() |

Sources: [httpx/_auth.py:62-111](), [tests/client/test_auth.py:137-160](), [docs/advanced/authentication.md:185-188]()

### Accessing Request and Response Bodies

Some authentication schemes need to read the request or response body. Set these flags on your `Auth` subclass:

```python
class ResponseBodyAuth(httpx.Auth):
    requires_request_body = False
    requires_response_body = True
    
    def auth_flow(self, request):
        request.headers["Authorization"] = "initial"
        response = yield request
        
        # Response body is available because requires_response_body=True
        data = response.text
        request.headers["Authorization"] = data
        
        yield request
```

| Flag | Effect |
|------|--------|
| `requires_request_body = True` | Request body is read (`request.read()` / `request.aread()`) before auth flow starts [httpx/_auth.py:71-72, 96-97]() |
| `requires_response_body = True` | Response body is read (`response.read()` / `response.aread()`) before being sent into generator [httpx/_auth.py:79-80, 104-105]() |

Sources: [httpx/_auth.py:35-36](), [tests/client/test_auth.py:115-135](), [docs/advanced/authentication.md:125-152]()

## Implementation Details

### Cookie Handling in Authentication Flows

During multi-step authentication (like DigestAuth), cookies from intermediate responses are automatically preserved in the retry request.

```python
# Server sends Set-Cookie in 401 response
# DigestAuth automatically includes that cookie in retry request
auth = httpx.DigestAuth("user", "pass")
response = client.get("https://example.com", auth=auth)
```

The implementation uses `Cookies.set_cookie_header()` to copy cookies from the 401 response into the retry request [httpx/_auth.py:220-222]().

Sources: [httpx/_auth.py:220-222](), [tests/test_auth.py:107-144]()

### Security and Header Hiding

The `Authorization` header is automatically marked as sensitive. WhenCredentials are embedded in URLs, the password is hidden in `repr()`:

```python
url = httpx.URL("https://user:password@example.com/")
print(repr(url))
# Output: URL('https://user:[secure]@example.com/')
```

Sources: [tests/client/test_auth.py:303-320]()

### Type Conversion

The `auth` parameter accepts multiple types:

| Input Type | Conversion |
|------------|------------|
| `tuple[str, str]` | Converted to `BasicAuth` [httpx/_auth.py:126-129]() |
| `Auth` subclass | Used directly |
| Callable `(Request) -> Request` | Wrapped in `FunctionAuth` [httpx/_auth.py:113-117]() |
| `None` | No authentication |

Sources: [httpx/_auth.py:113-124](), [tests/client/test_auth.py:339-354](), [docs/advanced/authentication.md:87-95]()

---

# Page: Client API

# Client API

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_client.py](httpx/_client.py)
- [tests/client/test_async_client.py](tests/client/test_async_client.py)
- [tests/client/test_client.py](tests/client/test_client.py)

</details>



This page provides a comprehensive guide to the `Client` and `AsyncClient` classes in httpx, which are the primary interfaces for making HTTP requests with connection pooling, configuration management, and advanced features. These classes offer both synchronous and asynchronous APIs for building and sending HTTP requests.

For basic request patterns without persistent connections, see [Making Requests](#2.1). For details on transport implementations and connection management, see [Transport System](#5).

## Client Class Hierarchy

httpx implements a class hierarchy where both synchronous and asynchronous clients inherit from a common base class that provides shared functionality.

```mermaid
graph TB
    BaseClient["httpx.BaseClient"]
    Client["httpx.Client"]
    AsyncClient["httpx.AsyncClient"]
    UseClientDefault["httpx.USE_CLIENT_DEFAULT"]
    ClientState["httpx.ClientState"]
    
    BaseClient --> Client
    BaseClient --> AsyncClient
    
    BaseClient -.-> UseClientDefault
    BaseClient -.-> ClientState
    
    Client -.-> BoundSyncStream["httpx.BoundSyncStream"]
    AsyncClient -.-> BoundAsyncStream["httpx.BoundAsyncStream"]
    
    subgraph "Core Methods"
        BuildRequest["build_request()"]
        Send["send() / async send()"]
        HTTPMethods["get(), post(), put(), etc."]
        StreamMethod["stream() / async stream()"]
    end
    
    BaseClient --> BuildRequest
    Client --> Send
    AsyncClient --> Send
    Client --> HTTPMethods
    AsyncClient --> HTTPMethods
    Client --> StreamMethod
    AsyncClient --> StreamMethod
```

Sources: [httpx/_client.py:188-593](), [httpx/_client.py:594-1306](), [httpx/_client.py:1307-1932]()

## BaseClient: Shared Foundation

The `BaseClient` class provides common functionality shared between synchronous and asynchronous implementations. It handles request building, configuration management, and redirect processing.

| Configuration Property | Type | Purpose |
|------------------------|------|---------|
| `auth` | `AuthTypes` | Authentication configuration [httpx/_client.py:208]() |
| `params` | `QueryParams` | Default query parameters [httpx/_client.py:209]() |
| `headers` | `Headers` | Default request headers [httpx/_client.py:210]() |
| `cookies` | `Cookies` | Cookie management [httpx/_client.py:211]() |
| `timeout` | `Timeout` | Request timeout configuration [httpx/_client.py:212]() |
| `base_url` | `URL` | Base URL for relative requests [httpx/_client.py:206]() |
| `follow_redirects` | `bool` | Automatic redirect following [httpx/_client.py:213]() |
| `max_redirects` | `int` | Maximum redirect limit [httpx/_client.py:214]() |
| `event_hooks` | `dict` | Request/response event hooks [httpx/_client.py:215-218]() |

The `BaseClient` maintains a `ClientState` enum with three states: `UNOPENED`, `OPENED`, and `CLOSED` to track the client lifecycle [httpx/_client.py:125-137]().

Sources: [httpx/_client.py:188-593](), [httpx/_client.py:125-137]()

## Request Building and Merging

The client API provides sophisticated request building through the `build_request()` method, which merges client-level defaults with request-specific parameters.

```mermaid
graph LR
    ClientDefaults["Client Defaults"]
    RequestParams["Request Parameters"]
    MergedRequest["httpx.Request"]
    
    subgraph "Merging Logic in build_request()"
        URLMerge["_merge_url()"]
        HeaderMerge["_merge_headers()"]
        CookieMerge["_merge_cookies()"]
        ParamMerge["_merge_queryparams()"]
    end
    
    ClientDefaults --> URLMerge
    RequestParams --> URLMerge
    URLMerge --> MergedRequest
    
    ClientDefaults --> HeaderMerge
    RequestParams --> HeaderMerge
    HeaderMerge --> MergedRequest
    
    ClientDefaults --> CookieMerge
    RequestParams --> CookieMerge
    CookieMerge --> MergedRequest
    
    ClientDefaults --> ParamMerge
    RequestParams --> ParamMerge
    ParamMerge --> MergedRequest
```

The merging process follows these rules:
- Base URLs are joined with relative request URLs using `_merge_url` [httpx/_client.py:391-411]().
- Headers are merged with request headers taking precedence in `_merge_headers` [httpx/_client.py:424-431]().
- Cookies are combined from both client and request in `_merge_cookies` [httpx/_client.py:413-422]().
- Query parameters are merged using `_merge_queryparams` [httpx/_client.py:433-443]().

Sources: [httpx/_client.py:340-389](), [httpx/_client.py:391-443]()

## Synchronous Client

The `Client` class provides a thread-safe synchronous HTTP client with connection pooling and advanced features. For details, see [Synchronous Client](#3.1).

### Core Request Methods

The `Client` exposes standard HTTP methods like `get()`, `post()`, `put()`, etc., which internally call `request()` [httpx/_client.py:771-825]().

### Transport and Connection Management

The `Client` manages transports through URL pattern matching, enabling different transports for different URL patterns including proxy support.

```mermaid
graph TB
    Client["httpx.Client"]
    Transport["_transport: BaseTransport"]
    Mounts["_mounts: dict[URLPattern, BaseTransport]"]
    URLPattern["httpx.URLPattern"]
    
    subgraph "Transport Implementations"
        HTTPTransport["httpx.HTTPTransport"]
        ASGITransport["httpx.ASGITransport"]
        WSGITransport["httpx.WSGITransport"]
    end
    
    Client --> Transport
    Client --> Mounts
    Mounts --> URLPattern
    
    URLPattern --> HTTPTransport
    URLPattern --> ASGITransport
    URLPattern --> WSGITransport
    
    Client --> TransportForURL["_transport_for_url()"]
    TransportForURL --> URLPattern
```

The transport selection process uses `_transport_for_url()` [httpx/_client.py:760-769]() to match URLs against configured patterns in `_mounts`.

Sources: [httpx/_client.py:594-1306](), [httpx/_client.py:718-758](), [httpx/_client.py:760-769]()

## Asynchronous Client

The `AsyncClient` class provides the same interface as `Client` but with async/await support for non-blocking I/O operations. For details, see [Asynchronous Client](#3.2).

### Async Method Variants

All client methods have async counterparts:
- `await client.request()` [httpx/_client.py:1501-1540]()
- `await client.get()`, `await client.post()`, etc. [httpx/_client.py:1447-1500]()
- `async with client.stream()` for async streaming [httpx/_client.py:1542-1592]()
- `await client.send()` for sending pre-built requests [httpx/_client.py:1594-1643]()

### Context Manager Support

The `AsyncClient` supports the async context manager protocol, ensuring proper cleanup of connections via `aclose()` [httpx/_client.py:1933-1948]().

Sources: [httpx/_client.py:1307-1932](), [httpx/_client.py:1933-1976]()

## Request Processing Pipeline

Both client types follow a structured request processing pipeline including authentication, redirects, and event hooks.

```mermaid
graph TD
    BuildRequest["build_request()"]
    SendRequest["send()"]
    AuthFlow["_send_handling_auth()"]
    RedirectFlow["_send_handling_redirects()"]
    SingleRequest["_send_single_request()"]
    TransportCall["transport.handle_request()"]
    
    subgraph "Event Hooks Execution"
        RequestHook["request hooks"]
        ResponseHook["response hooks"]
    end
    
    BuildRequest --> SendRequest
    SendRequest --> AuthFlow
    AuthFlow --> RedirectFlow
    RedirectFlow --> RequestHook
    RequestHook --> SingleRequest
    SingleRequest --> TransportCall
    TransportCall --> ResponseHook
```

The pipeline handles:
- Authentication flow through `_send_handling_auth` [httpx/_client.py:930-962]().
- Redirect detection and following in `_send_handling_redirects` [httpx/_client.py:964-999]().
- Event hook execution at request and response stages [httpx/_client.py:976-982]().
- Response stream binding for elapsed time tracking via `BoundSyncStream` or `BoundAsyncStream` [httpx/_client.py:1019-1021]().

Sources: [httpx/_client.py:879-928](), [httpx/_client.py:930-962](), [httpx/_client.py:964-999](), [httpx/_client.py:1001-1034]()

## Configuration Management

Client configuration is managed through properties that provide validation and type conversion. For details on passing data, see [Request Parameters](#3.3).

| Configuration | Setter Behavior | Default Value |
|---------------|----------------|---------------|
| `timeout` | Converts to `Timeout` object | `DEFAULT_TIMEOUT_CONFIG` [httpx/_client.py:212]() |
| `auth` | Builds `Auth` instance | `None` [httpx/_client.py:208]() |
| `base_url` | Ensures trailing slash | `""` [httpx/_client.py:206]() |

The `USE_CLIENT_DEFAULT` constant [httpx/_client.py:94-114]() is used to distinguish between unset parameters (which use client defaults) and explicitly disabled parameters (like `timeout=None`).

Sources: [httpx/_client.py:94-114](), [httpx/_client.py:254-338](), [httpx/_client.py:445-473]()

## Redirects and Streaming

- **Redirects**: Managed by the client when `follow_redirects` is enabled. For details, see [Redirects and History](#3.4).
- **Streaming**: Supported via `client.stream()` and `client.astream()`. For details, see [Streaming](#3.5).

Streaming responses use `BoundSyncStream` [httpx/_client.py:139-160]() and `BoundAsyncStream` [httpx/_client.py:162-183]() wrappers to track `response.elapsed` and ensure proper closure.

Sources: [httpx/_client.py:139-183](), [httpx/_client.py:827-877](), [httpx/_client.py:1542-1592]()

---

# Page: Synchronous Client

# Synchronous Client

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_client.py](httpx/_client.py)
- [tests/client/test_async_client.py](tests/client/test_async_client.py)
- [tests/client/test_client.py](tests/client/test_client.py)

</details>



The `Client` class in HTTPX provides a thread-safe HTTP client with connection pooling, lifecycle management, and comprehensive configuration options for making synchronous HTTP requests. It inherits from `BaseClient` and implements transport-level connection management through the underlying `HTTPTransport` system. For asynchronous request handling, see [Asynchronous Client](#3.2).

## Client Class Architecture

The `Client` class extends `BaseClient` and manages connection pooling through transport instances. Each client maintains a default `_transport` and optional mounted transports in `_mounts` for different URL patterns.

### Client Class Hierarchy and Core Components

```mermaid
graph TD
    BaseClient["BaseClient"] --> Client["Client"]
    BaseClient --> AsyncClient["AsyncClient"]
    
    Client --> _transport["_transport: BaseTransport"]
    Client --> _mounts["_mounts: dict[URLPattern, BaseTransport]"]
    Client --> _state["_state: ClientState"]
    
    _transport --> HTTPTransport["HTTPTransport"]
    
    _mounts --> URLPattern["URLPattern"]
    
    _state --> UNOPENED["UNOPENED"]
    _state --> OPENED["OPENED"] 
    _state --> CLOSED["CLOSED"]
    
    Client --> request_methods["Request Methods"]
    request_methods --> get["get()"]
    request_methods --> post["post()"]
    request_methods --> send["send()"]
    request_methods --> stream["stream()"]
```

Sources: [httpx/_client.py:594-716](), [httpx/_client.py:125-136]()

## Client Initialization and Configuration

The `Client` can be instantiated with numerous configuration options. During initialization, it sets up the default `HTTPTransport` [httpx/_client.py:685-716]() and handles proxy configurations via `_get_environment_proxies` if `trust_env` is enabled [httpx/_client.py:722-726]().

```python
Client(
    auth=None,                  # Authentication credentials
    params=None,                # Default query parameters
    headers=None,               # Default headers
    cookies=None,               # Default cookies
    verify=True,                # SSL verification
    cert=None,                  # Client-side certificates
    http1=True,                 # HTTP/1.1 support
    http2=False,                # HTTP/2 support
    proxy=None,                 # Proxy configuration
    mounts=None,                # URL mounts for custom transports
    timeout=DEFAULT_TIMEOUT_CONFIG,
    follow_redirects=False,     # Auto-follow redirects
    limits=DEFAULT_LIMITS,      # Connection pool limits
    event_hooks=None,           # Request/response hooks
    base_url="",                # Base URL for relative URLs
    transport=None,             # Custom transport
    app=None,                   # WSGI app
    trust_env=True,             # Trust environment variables
    default_encoding="utf-8"    # Default text encoding
)
```

The client should typically be used as a context manager to ensure proper resource cleanup:

```python
with httpx.Client() as client:
    response = client.get('https://example.org')
```

Sources: [httpx/_client.py:639-694](), [tests/client/test_client.py:16-31](), [tests/client/test_client.py:304-323]()

## Method Structure

The `Client` class implements a structured method hierarchy to handle the HTTP request lifecycle. High-level methods like `get()` and `post()` are wrappers around the generic `request()` method [httpx/_client.py:771-825]().

```mermaid
graph TD
    Client["Client"] --> PublicAPI["Public API"]
    Client --> InternalAPI["Internal API"]
    
    PublicAPI --> request["request()"]
    PublicAPI --> get["get()"]
    PublicAPI --> post["post()"]
    PublicAPI --> put["put()"]
    PublicAPI --> patch["patch()"]
    PublicAPI --> delete["delete()"]
    PublicAPI --> head["head()"]
    PublicAPI --> options["options()"]
    PublicAPI --> build_request["build_request()"]
    PublicAPI --> send["send()"]
    PublicAPI --> stream["stream()"]
    PublicAPI --> close["close()"]
    
    InternalAPI --> _send_handling_auth["_send_handling_auth()"]
    InternalAPI --> _send_handling_redirects["_send_handling_redirects()"]
    InternalAPI --> _send_single_request["_send_single_request()"]
    InternalAPI --> _transport_for_url["_transport_for_url()"]
    InternalAPI --> _build_redirect_request["_build_redirect_request()"]
    
    request --> build_request
    request --> send
    stream --> build_request
    stream --> send
    
    send --> _send_handling_auth
    _send_handling_auth --> _send_handling_redirects
    _send_handling_redirects --> _send_single_request
    _send_handling_redirects --> _build_redirect_request
    _send_single_request --> _transport_for_url
```

Sources: [httpx/_client.py:771-825](), [httpx/_client.py:879-1034]()

## Making Requests

The `Client` provides methods for all standard HTTP methods. Each method takes at minimum a URL parameter and returns a `Response` object [httpx/_client.py:1036-1093]():

| Method | Description |
|--------|-------------|
| `get(url, **kwargs)` | Send a GET request |
| `post(url, **kwargs)` | Send a POST request |
| `put(url, **kwargs)` | Send a PUT request |
| `patch(url, **kwargs)` | Send a PATCH request |
| `delete(url, **kwargs)` | Send a DELETE request |
| `head(url, **kwargs)` | Send a HEAD request |
| `options(url, **kwargs)` | Send an OPTIONS request |

All request methods accept common parameters such as `params`, `headers`, `cookies`, `auth`, `follow_redirects`, and `timeout`. These are merged with client-level defaults [httpx/_client.py:773-789]().

For more control, you can use `build_request()` to create a request object and then `send()` to transmit it [tests/client/test_client.py:47-60]().

Sources: [httpx/_client.py:771-825](), [httpx/_client.py:1036-1093](), [tests/client/test_client.py:47-89]()

## Request and Response Flow

When making a request, the client follows this process flow, moving from high-level request building to low-level transport execution.

### Request Processing Flow

```mermaid
sequenceDiagram
    participant User as "User Code"
    participant Client as "Client"
    participant BaseClient as "BaseClient"
    participant Transport as "_transport_for_url()"
    participant HTTPTransport as "HTTPTransport"
    participant Server as "HTTP Server"
    
    User->>Client: client.get(url, **kwargs)
    Client->>Client: build_request("GET", url, **kwargs)
    Client->>Client: send(request, auth, follow_redirects)
    
    Note over Client: State check: CLOSED → RuntimeError
    Client->>Client: _state = ClientState.OPENED
    
    Client->>BaseClient: _build_request_auth(request, auth)
    Client->>Client: _send_handling_auth(request, auth, follow_redirects, history)
    Client->>Client: _send_handling_redirects(request, follow_redirects, history)
    
    loop Event hooks
        Client->>Client: event_hooks["request"](request)
    end
    
    Client->>Client: _send_single_request(request)
    Client->>Transport: _transport_for_url(request.url)
    Transport->>HTTPTransport: Selected transport
    
    HTTPTransport->>Server: handle_request(request)
    Server->>HTTPTransport: Response
    HTTPTransport->>Client: Response
    
    Client->>Client: BoundSyncStream(response.stream, response, start_time)
    Client->>Client: cookies.extract_cookies(response)
    
    loop Event hooks
        Client->>Client: event_hooks["response"](response)
    end
    
    Client->>User: Return Response
```

Key aspects of the request flow:
1. **State Validation**: Client state validation prevents usage after closure [httpx/_client.py:885-886]().
2. **Transport Selection**: Selection based on URL patterns and mounts [httpx/_client.py:1263-1273]().
3. **Response Binding**: Response streams are wrapped in `BoundSyncStream` to track `response.elapsed` time [httpx/_client.py:139-161]().
4. **Cookie Extraction**: `cookies.extract_cookies(response)` maintains session state [httpx/_client.py:1016]().

Sources: [httpx/_client.py:879-929](), [httpx/_client.py:930-962](), [httpx/_client.py:964-999](), [httpx/_client.py:1001-1034](), [httpx/_client.py:139-161]()

## Streaming Responses

For large responses, the `stream()` method allows handling data without loading everything into memory at once [httpx/_client.py:827-877]():

```python
with client.stream("GET", "https://example.org") as response:
    for chunk in response.iter_bytes():
        # Process each chunk
        pass
```

The `stream()` method returns a response within a context manager. If the response is not read within the block, the connection is closed [httpx/_client.py:869-877]().

Sources: [httpx/_client.py:827-877](), [tests/client/test_client.py:92-121]()

## Connection Pooling and Lifecycle Management

### Client State Management

The `Client` tracks its lifecycle through the `ClientState` enum [httpx/_client.py:125-136]().

### Client Lifecycle State Transitions

```mermaid
stateDiagram-v2
    [*] --> UNOPENED: Client()
    UNOPENED --> OPENED: first request or __enter__()
    UNOPENED --> OPENED: send() called
    OPENED --> CLOSED: close() or __exit__()
    CLOSED --> [*]: garbage collection
    
    UNOPENED: ClientState.UNOPENED
    OPENED: ClientState.OPENED  
    CLOSED: ClientState.CLOSED
```

| State | Description |
|-------|-------------|
| `UNOPENED` | Client instantiated but unused. |
| `OPENED` | Client has sent requests or entered context. |
| `CLOSED` | Client has been closed; further requests raise `RuntimeError`. |

### Context Manager Usage

The client supports the context manager protocol for automatic resource cleanup [httpx/_client.py:1275-1304]():

```python
# Automatic lifecycle management
with httpx.Client() as client:
    response = client.get('https://example.org')
# Transport and connections automatically closed via client.close()
```

Sources: [httpx/_client.py:125-136](), [httpx/_client.py:223-228](), [httpx/_client.py:1275-1304](), [httpx/_client.py:760-769]()

## Transport System and Connection Management

### Transport Initialization

The `Client` initializes transports during construction, setting up connection pools and proxy configurations [httpx/_client.py:718-758]().

### Transport Selection

The client uses `_transport_for_url()` to select the appropriate transport for each request based on URL pattern matching [httpx/_client.py:1263-1273]():

```python
def _transport_for_url(self, url: URL) -> BaseTransport:
    """Returns the transport instance for a given URL."""
    for pattern, transport in self._mounts.items():
        if pattern.matches(url):
            return self._transport if transport is None else transport
    return self._transport
```

### Transport Lifecycle

Transport instances are managed through the client lifecycle. Calling `close()` iterates through all mounts and the base transport to shut them down [httpx/_client.py:760-769]().

Sources: [httpx/_client.py:718-758](), [httpx/_client.py:760-769](), [httpx/_client.py:1263-1273](), [httpx/_client.py:685-716]()

## URL Handling and Base URLs

The client supports a `base_url` parameter which is used for resolving relative URLs [httpx/_client.py:206]().

```python
client = httpx.Client(base_url="https://api.example.org/v1/")
response = client.get("users")  # https://api.example.org/v1/users
```

URL merging is handled by `_merge_url()`, which applies `base_url` if the request URL is relative [httpx/_client.py:391-411]().

Sources: [httpx/_client.py:206](), [httpx/_client.py:391-411](), [tests/client/test_client.py:184-229]()

## Header, Cookie, and Parameter Merging

When making requests, the client merges its own defaults with request-specific values:
- **Headers**: Client headers are merged with request headers [httpx/_client.py:413-432]().
- **Cookies**: Request cookies are merged into the client's `CookieJar` [httpx/_client.py:434-443]().
- **Parameters**: Query parameters are merged during request building [httpx/_client.py:365-375]().

Sources: [httpx/_client.py:365-375](), [httpx/_client.py:413-443]()

---

# Page: Asynchronous Client

# Asynchronous Client

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.github/workflows/publish.yml](.github/workflows/publish.yml)
- [.github/workflows/test-suite.yml](.github/workflows/test-suite.yml)
- [docs/async.md](docs/async.md)
- [httpx/_client.py](httpx/_client.py)
- [tests/client/test_async_client.py](tests/client/test_async_client.py)
- [tests/client/test_client.py](tests/client/test_client.py)

</details>



This document covers the `AsyncClient` class, httpx's asynchronous HTTP client implementation. The `AsyncClient` provides the same HTTP functionality as the synchronous [Synchronous Client](#3.1) but uses `async`/`await` syntax for non-blocking I/O operations and efficient concurrency.

## Overview

The `AsyncClient` class enables asynchronous HTTP requests using Python's async/await syntax. It provides connection pooling, request/response processing, and all HTTP methods in an async-compatible interface. `AsyncClient` is essential for async web frameworks (like Starlette or FastAPI) and applications that need to handle many concurrent HTTP requests efficiently. It supports multiple backends including `asyncio` and `trio` [docs/async.md:131-175]().

**AsyncClient Class Architecture**

```mermaid
classDiagram
    class BaseClient {
        +__init__(auth, params, headers, cookies, timeout, follow_redirects, max_redirects, event_hooks, base_url, trust_env, default_encoding)
        +build_request(method, url, ...) Request
        +_merge_url(url) URL
        +_merge_headers(headers) HeaderTypes
        +_merge_cookies(cookies) CookieTypes
        +_merge_queryparams(params) QueryParamTypes
        +_build_auth(auth) Auth
        +_build_redirect_request(request, response) Request
        -_auth Auth
        -_params QueryParams
        -_headers Headers
        -_cookies Cookies
        -_timeout Timeout
        -_base_url URL
        -_state ClientState
    }

    class AsyncClient {
        +__init__(auth, params, headers, cookies, verify, cert, trust_env, http1, http2, proxy, mounts, timeout, follow_redirects, limits, max_redirects, event_hooks, base_url, transport, default_encoding)
        +async __aenter__() AsyncClient
        +async __aexit__(exc_type, exc_value, traceback)
        +async aclose()
        +async request(method, url, ...) Response
        +async stream(method, url, ...)
        +async send(request, stream, auth, follow_redirects) Response
        +async get(url, ...) Response
        +async post(url, ...) Response
        +async put(url, ...) Response
        +async patch(url, ...) Response
        +async delete(url, ...) Response
        +async head(url, ...) Response
        +async options(url, ...) Response
        -_transport AsyncHTTPTransport
        -_mounts dict[URLPattern, AsyncBaseTransport]
    }

    class AsyncHTTPTransport {
        +async handle_request(request) Response
        +async aclose()
    }

    class AsyncBaseTransport {
        +async handle_request(request) Response
        +async aclose()
    }

    BaseClient <|-- AsyncClient
    AsyncClient --> AsyncHTTPTransport
    AsyncHTTPTransport --|> AsyncBaseTransport
```

Sources: [httpx/_client.py:188-221](), [httpx/_client.py:1386-1870](), [httpx/_transports/base.py:48-63]()

## Basic Usage

`AsyncClient` requires async/await syntax and should ideally be used as an async context manager to ensure connection pools are closed correctly [docs/async.md:47-65]().

```python
async with httpx.AsyncClient() as client:
    response = await client.get('https://example.com')
```

The `AsyncClient` supports the same HTTP methods as the synchronous client, but all methods are coroutines that must be awaited.

**Async Request Processing Flow**

```mermaid
sequenceDiagram
    participant User as "User Code"
    participant AC as "httpx.AsyncClient"
    participant BC as "httpx.BaseClient"
    participant T as "httpx.AsyncHTTPTransport"
    participant HC as "httpcore.AsyncConnectionPool"

    User ->>+ AC: await client.get(url)
    AC ->>+ BC: build_request("GET", url, ...)
    BC -->>- AC: httpx.Request
    AC ->>+ AC: _build_request_auth(request, auth)
    AC -->>- AC: httpx.Auth
    AC ->>+ AC: _send_handling_auth(request, auth, ...)
    AC ->>+ AC: _send_handling_redirects(request, ...)
    AC ->>+ AC: _send_single_request(request)
    AC ->>+ T: await transport.handle_request(request)
    T ->>+ HC: async handle_request
    HC -->>- T: raw response
    T -->>- AC: httpx.Response
    AC ->>+ AC: wrap with BoundAsyncStream
    AC -->>- AC: httpx.Response
    AC -->>- AC: httpx.Response
    AC -->>- AC: httpx.Response
    AC -->>- AC: httpx.Response
    AC -->>- User: httpx.Response
```

Sources: [httpx/_client.py:1600-1616](), [httpx/_client.py:1758-1781](), [httpx/_client.py:1808-1870](), [tests/client/test_async_client.py:12-21]()

## Context Management and Lifecycle

`AsyncClient` implements the async context manager protocol (`__aenter__` and `__aexit__`) for proper resource management [httpx/_client.py:1445-1463]().

| Method | Purpose | When Called |
|--------|---------|-------------|
| `__aenter__()` | Initialize client resources and enter context | `async with AsyncClient()` entry |
| `__aexit__()` | Clean up resources and close transports | Context exit or exception |
| `aclose()` | Explicitly close connections and transports | Manual cleanup when not using `async with` |

**AsyncClient Lifecycle States**

```mermaid
stateDiagram-v2
    [*] --> UNOPENED: AsyncClient()
    UNOPENED --> OPENED: first request or __aenter__
    OPENED --> CLOSED: __aexit__ or aclose()
    CLOSED --> [*]
    
    note right of UNOPENED : Client instantiated via __init__
    note right of OPENED : Transports initialized and active
    note right of CLOSED : aclose() completed, client unusable
```

The client state is tracked via the `ClientState` enum: `UNOPENED`, `OPENED`, or `CLOSED` [httpx/_client.py:125-137]().

Sources: [httpx/_client.py:1386-1410](), [httpx/_client.py:1445-1491](), [httpx/_client.py:125-137]()

## Async Request Methods

All primary HTTP methods in `AsyncClient` are asynchronous coroutines [docs/async.md:33-45]():

| Method | Signature | Purpose |
|--------|-----------|---------|
| `request()` | `async request(method, url, ...)` | Generic HTTP request [httpx/_client.py:1564-1599]() |
| `get()` | `async get(url, ...)` | HTTP GET request [httpx/_client.py:1670-1681]() |
| `post()` | `async post(url, ...)` | HTTP POST request [httpx/_client.py:1694-1707]() |
| `put()` | `async put(url, ...)` | HTTP PUT request [httpx/_client.py:1709-1722]() |
| `patch()` | `async patch(url, ...)` | HTTP PATCH request [httpx/_client.py:1737-1750]() |
| `delete()` | `async delete(url, ...)` | HTTP DELETE request [httpx/_client.py:1752-1763]() |
| `head()` | `async head(url, ...)` | HTTP HEAD request [httpx/_client.py:1683-1692]() |
| `options()` | `async options(url, ...)` | HTTP OPTIONS request [httpx/_client.py:1724-1735]() |
| `send()` | `async send(request, ...)` | Send pre-built `Request` [httpx/_client.py:1600-1616]() |

When sending a streaming request body, `AsyncClient` expects an async bytes generator [docs/async.md:108-116]():
```python
async def upload_bytes():
    yield b"chunk"

await client.post(url, content=upload_bytes())
```

Sources: [httpx/_client.py:1670-1783](), [docs/async.md:108-116]()

## Streaming Support

`AsyncClient` provides async streaming capabilities through the `stream()` context manager and async response iterators [docs/async.md:67-85]().

**Async Streaming Methods**

| Response Method | Purpose |
|----------------|---------|
| `aread()` | Read entire response content asynchronously [httpx/_models.py:917-935]() |
| `aiter_bytes()` | Iterate response as byte chunks [httpx/_models.py:821-831]() |
| `aiter_text()` | Iterate response as text chunks [httpx/_models.py:833-847]() |
| `aiter_lines()` | Iterate response as text lines [httpx/_models.py:849-862]() |
| `aiter_raw()` | Iterate raw response bytes (no decoding) [httpx/_models.py:810-819]() |
| `aclose()` | Close response stream [httpx/_models.py:937-950]() |

The `BoundAsyncStream` ensures that `response.elapsed` is calculated correctly once the stream is closed [httpx/_client.py:162-183]().

**Stream Processing Architecture**

```mermaid
flowchart TD
    SC["client.stream() context"] --> BR["build_request()"]
    BR --> SR["send(stream=True)"]
    SR --> AST["httpx.AsyncHTTPTransport"]
    AST --> R["httpx.Response"]
    R --> BAS["httpx.BoundAsyncStream"]
    BAS --> AI["async iteration (aiter_bytes, etc.)"]
    AI --> UC["User Code"]
    
    SC --> AC["automatic await response.aclose()"]
    AC --> CC["connection released to pool"]
```

Sources: [httpx/_client.py:1617-1669](), [httpx/_client.py:162-183](), [docs/async.md:67-85]()

## Transport and Connection Management

`AsyncClient` uses `AsyncHTTPTransport` by default. It manages a connection pool and can route requests to different transports based on URL patterns via the `mounts` parameter [httpx/_client.py:1411-1444]().

**Transport Configuration**

```mermaid
flowchart LR
    AC["httpx.AsyncClient"] --> TFU["_transport_for_url()"]
    TFU --> M["_mounts dict"]
    M --> UP["httpx.URLPattern matching"]
    UP --> AT["AsyncBaseTransport selection"]
    
    AC --> DT["_transport (default)"]
    DT --> AHT["httpx.AsyncHTTPTransport"]
    
    AC --> MT["mounted transports"]
    MT --> ASGI["httpx.ASGITransport"]
    MT --> Mock["httpx.MockTransport"]
```

The transport initialization determines whether HTTP/1.1 or HTTP/2 is used based on the `http1` and `http2` arguments [httpx/_client.py:1411-1444]().

Sources: [httpx/_client.py:1411-1444](), [httpx/_client.py:1492-1538](), [httpx/_client.py:1564-1599](), [docs/async.md:118-130]()

## Configuration Options

`AsyncClient` inherits from `BaseClient` and shares most configuration parameters [httpx/_client.py:188-221]().

| Parameter | Type | Purpose |
|-----------|------|---------|
| `auth` | `AuthTypes` | Default authentication [httpx/_client.py:208]() |
| `params` | `QueryParamTypes` | Default query parameters [httpx/_client.py:209]() |
| `headers` | `HeaderTypes` | Default request headers [httpx/_client.py:210]() |
| `cookies` | `CookieTypes` | Default cookies [httpx/_client.py:211]() |
| `timeout` | `TimeoutTypes` | Default timeout [httpx/_client.py:212]() |
| `limits` | `Limits` | Connection pool limits [httpx/_client.py:1399]() |
| `proxy` | `ProxyTypes` | Proxy configuration [httpx/_client.py:1396]() |
| `mounts` | `Mapping[str, AsyncBaseTransport]` | Custom transport mounts [httpx/_client.py:1397]() |
| `http2` | `bool` | Enable HTTP/2 support [httpx/_client.py:1395]() |
| `follow_redirects`| `bool` | Automatic redirect following [httpx/_client.py:213]() |
| `base_url` | `URL \| str` | Base URL for relative requests [httpx/_client.py:206]() |

Sources: [httpx/_client.py:1386-1410](), [httpx/_client.py:189-221]()

---

# Page: Request Parameters

# Request Parameters

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_client.py](httpx/_client.py)
- [httpx/_content.py](httpx/_content.py)
- [tests/client/test_cookies.py](tests/client/test_cookies.py)
- [tests/client/test_headers.py](tests/client/test_headers.py)
- [tests/client/test_properties.py](tests/client/test_properties.py)
- [tests/client/test_queryparams.py](tests/client/test_queryparams.py)
- [tests/test_content.py](tests/test_content.py)

</details>



This document covers the management of HTTP request parameters in `httpx`, including headers, query parameters, cookies, and request body content. It explains how these parameters are configured at both the client level (applying to all requests) and individual request level, as well as the internal encoding mechanisms.

## Parameter Management Architecture

`httpx` provides a flexible parameter management system where request parameters can be configured at multiple levels. The library distinguishes between raw content (`content`), form data (`data`), JSON payloads (`json`), and file uploads (`files`).

```mermaid
graph TB
    subgraph "Parameter Sources"
        ClientLevel["Client-Level Parameters<br/>client.headers, client.cookies, client.params"]
        RequestLevel["Request-Level Parameters<br/>client.get(headers=..., params=..., data=..., json=...)"]
        DefaultHeaders["Default Headers<br/>User-Agent, Accept, etc."]
    end
    
    subgraph "Encoding & Merge Logic"
        HeaderMerger["Header Merger<br/>_merge_headers()"]
        ContentEncoder["Content Encoder<br/>encode_request()"]
        ParamMerger["Query Param Merger<br/>QueryParams.merge()"]
    end
    
    subgraph "Final Request Entity"
        FinalHeaders["Final Headers<br/>httpx.Headers"]
        FinalParams["Final Query Params<br/>httpx.QueryParams"]
        FinalStream["Request Stream<br/>SyncByteStream / AsyncByteStream"]
    end
    
    DefaultHeaders --> HeaderMerger
    ClientLevel --> HeaderMerger
    ClientLevel --> ParamMerger
    RequestLevel --> HeaderMerger
    RequestLevel --> ParamMerger
    RequestLevel --> ContentEncoder
    
    HeaderMerger --> FinalHeaders
    ParamMerger --> FinalParams
    ContentEncoder --> FinalStream
    ContentEncoder -.->|Adds Content-Type/Length| FinalHeaders
    
    FinalHeaders --> HttpRequest["httpx.Request"]
    FinalParams --> HttpRequest
    FinalStream --> HttpRequest
```

Sources: [httpx/_client.py:188-222](), [httpx/_content.py:186-215](), [tests/client/test_headers.py:46-87]()

## Headers Management

Headers can be configured at both client and request levels. Request-level headers take precedence over client-level headers for the same header name.

### Client-Level Headers
Client-level headers are set during client initialization or by modifying the `client.headers` property. The `BaseClient` initializes headers as an `httpx.Headers` object [httpx/_client.py:210]().

```python
client = httpx.Client(headers={"User-Agent": "my-app/1.0"})
client.headers["Authorization"] = "Bearer token"
```

### Request-Level Headers
Request-level headers are passed to individual request methods and are merged with client-level headers [tests/client/test_headers.py:46-65]().

### Header Merging and Defaults
1. **Defaults**: `httpx` automatically includes `User-Agent` (e.g., `python-httpx/0.x.x`) and `Accept-Encoding` (gzip, deflate, br, zstd) [httpx/_client.py:119-122]().
2. **Merging**: If a request-level header conflicts with a client-level header, the request-level value is used [tests/client/test_headers.py:68-87]().
3. **Removal**: A default header can be removed by deleting it from `client.headers` [tests/client/test_headers.py:152-171]().

Sources: [httpx/_client.py:119-122](), [httpx/_client.py:210](), [tests/client/test_headers.py:46-87](), [tests/client/test_headers.py:152-171]()

## Query Parameters Management

Query parameters are handled by the `QueryParams` class, which supports multiple values and proper URL encoding.

### Client-Level Query Parameters
Initialized in `BaseClient` via the `params` argument [httpx/_client.py:209](). They can be passed as strings, dictionaries, or `QueryParams` objects [tests/client/test_queryparams.py:8-23]().

### Query Parameter Merging
Unlike headers, query parameters are merged by combining both client and request parameters. If a key exists in both, the request-level parameter typically overrides or appends depending on the specific merge logic [tests/client/test_queryparams.py:25-36]().

Sources: [httpx/_client.py:209](), [tests/client/test_queryparams.py:8-36]()

## Request Body Parameters

`httpx` uses the `encode_request` function in `httpx/_content.py` to transform various arguments into a standardized byte stream and associated headers.

| Argument | Input Type | Internal Handler | Resulting `Content-Type` |
|----------|------------|------------------|--------------------------|
| `content`| `bytes`, `str`, `Iterable`, `AsyncIterable` | `encode_content` | None (User defined) |
| `data`   | `dict`, `Mapping` | `encode_urlencoded_data` | `application/x-www-form-urlencoded` |
| `json`   | `Any` (JSON serializable) | `encode_json` | `application/json` |
| `files`  | `dict` (File-like objects) | `encode_multipart_data` | `multipart/form-data; boundary=...` |

### Encoding Logic Flow

```mermaid
graph LR
    subgraph "httpx.Request Initialization"
        Input[content, data, json, files]
        Dispatch{"Dispatch Logic<br/>encode_request()"}
    end

    Dispatch -->|json is set| JSON["encode_json()"]
    Dispatch -->|files is set| Multi["encode_multipart_data()"]
    Dispatch -->|data is dict| Form["encode_urlencoded_data()"]
    Dispatch -->|content is set| Raw["encode_content()"]

    JSON --> Stream["ByteStream"]
    Form --> Stream
    Raw --> Stream
    Multi --> MStream["MultipartStream"]
```

Sources: [httpx/_content.py:186-215](), [httpx/_content.py:107-133](), [httpx/_content.py:176-183]()

## Cookie Management

Cookies are managed via the `Cookies` class and integrated with the standard `http.cookiejar.CookieJar`.

### Client-Level Cookies
Cookies set on the client are persisted across requests [tests/client/test_cookies.py:151-169](). They are stored in `self._cookies` as an `httpx.Cookies` instance [httpx/_client.py:211]().

### Per-Request Cookies
Passing `cookies=...` directly to a request method (like `client.get(...)`) is **deprecated** and will emit a `DeprecationWarning` [tests/client/test_cookies.py:34-47](). Users should set cookies on the client or modify the `client.cookies` property directly.

Sources: [httpx/_client.py:211](), [tests/client/test_cookies.py:34-47](), [tests/client/test_cookies.py:151-169]()

## Parameter Types and Data Structures

`httpx` enforces specific types for parameters to ensure consistency.

- **`httpx.Headers`**: A case-insensitive multi-dict [tests/client/test_headers.py:175-185]().
- **`httpx.QueryParams`**: An immutable multi-dict for URL query strings [tests/client/test_queryparams.py:9-11]().
- **`httpx.Cookies`**: A wrapper around `CookieJar` for easy dictionary-like access [tests/client/test_properties.py:32-39]().

### Property Auto-Conversion
Assigning a dictionary to client properties like `client.headers` or `client.params` automatically converts them into their respective `httpx` classes [tests/client/test_properties.py:25-39]().

Sources: [httpx/_client.py:208-212](), [tests/client/test_properties.py:25-39]()

---

# Page: Redirects and History

# Redirects and History

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_client.py](httpx/_client.py)
- [tests/client/test_redirects.py](tests/client/test_redirects.py)

</details>



This document covers HTTP redirect handling in HTTPX's client API, including how to enable redirect following, access redirect history, and understand the behavior of different redirect status codes.

## Redirect Behavior Overview

HTTPX does not follow redirects by default, unlike some other HTTP libraries. This design choice prevents unnecessary network calls from being masked and gives developers explicit control over redirect handling. The default value for `follow_redirects` is `False` [httpx/_client.py:197-197]().

```mermaid
graph TD
    Request["httpx.Request"] --> Transport["BaseTransport.handle_request()"]
    Transport --> Server["HTTP Server"]
    Server --> RedirectResponse["httpx.Response (3xx)"]
    RedirectResponse --> CheckFollowFlag{"follow_redirects=True?"}
    CheckFollowFlag -->|No| ReturnResponse["Return Redirect Response"]
    CheckFollowFlag -->|Yes| BuildNextRequest["_build_redirect_request()"]
    BuildNextRequest --> FollowRedirect["Client._send_single_request()"]
    FollowRedirect --> UpdateHistory["Add to response.history"]
    UpdateHistory --> FinalResponse["Final Response"]
    ReturnResponse --> NextRequestProperty["response.next_request available"]
```

Sources: [httpx/_client.py:197-197](), [tests/client/test_redirects.py:116-152](), [httpx/_models.py:465-475]()

## Enabling Redirect Following

Redirects can be enabled per request using the `follow_redirects` parameter or configured on the `Client` or `AsyncClient` instance for all requests.

### Per-Request Redirects

```python
# Enable redirects for a specific request
response = client.get("http://github.com/", follow_redirects=True)
```

### Client-Wide Redirects

```python
# Enable redirects for all requests from this client
client = httpx.Client(follow_redirects=True)
```

The `BaseClient` stores this configuration in `self.follow_redirects` [httpx/_client.py:213-213](). If a request method omits the parameter, it defaults to `USE_CLIENT_DEFAULT`, which then pulls from the client's instance setting [httpx/_client.py:104-114]().

```mermaid
graph LR
    ClientInit["httpx.Client(follow_redirects=True)"] --> AllRequests["All Requests Follow Redirects"]
    RequestParam["client.get(..., follow_redirects=True)"] --> SingleRequest["Single Request Follows Redirects"]
    Default["Default Behavior"] --> NoRedirects["follow_redirects=False"]
```

Sources: [httpx/_client.py:188-213](), [httpx/_client.py:768-778](), [tests/client/test_redirects.py:116-138]()

## Response History

When redirects are followed, the `response.history` property contains a list of intermediate redirect responses in the order they were received [httpx/_models.py:456-463](). Each response in the history also maintains its own history chain.

```python
response = client.get("http://example.com/redirect", follow_redirects=True)
print(f"Final URL: {response.url}")
print(f"Redirects followed: {len(response.history)}")

# Access intermediate responses
for i, redirect_response in enumerate(response.history):
    print(f"Redirect {i}: {redirect_response.status_code} -> {redirect_response.headers['location']}")
```

```mermaid
graph TD
    OriginalRequest["Original Request"] --> Redirect1["301 Response"]
    Redirect1 --> Redirect2["302 Response"] 
    Redirect2 --> FinalResponse["200 Response"]
    
    FinalResponse --> History["response.history = [301, 302]"]
    Redirect2 --> History2["response.history[1].history = [301]"]
    Redirect1 --> History1["response.history[0].history = []"]
```

Sources: [httpx/_models.py:456-463](), [tests/client/test_redirects.py:229-241]()

## Next Request Handling

When redirects are disabled, the `response.next_request` property provides access to the next `httpx.Request` that would be made in the redirect chain [httpx/_models.py:465-475](). This allows manual control over redirect following.

```python
request = client.build_request("GET", "http://github.com/")
response = client.send(request, follow_redirects=False)

if response.next_request is not None:
    # Manually follow the redirect
    next_response = client.send(response.next_request)
```

```mermaid
graph LR
    DisabledRedirects["follow_redirects=False"] --> CheckNextRequest{"response.next_request?"}
    CheckNextRequest -->|Not None| ManualFollow["client.send(response.next_request)"]
    CheckNextRequest -->|None| NoMoreRedirects["No Further Redirects"]
    ManualFollow --> NextResponse["Next Response"]
```

Sources: [httpx/_models.py:465-475](), [tests/client/test_redirects.py:140-167]()

## HTTP Redirect Status Codes

HTTPX handles different HTTP redirect status codes according to RFC specifications. The behavior varies depending on whether the method should be preserved or changed to `GET`.

| Status Code | Name | Method Behavior | Body Behavior |
|-------------|------|-----------------|---------------|
| 301 | Moved Permanently | Preserved (usually) | Preserved |
| 302 | Found | Preserved (usually) | Preserved |
| 303 | See Other | Changed to GET | Removed |
| 307 | Temporary Redirect | Preserved | Preserved |
| 308 | Permanent Redirect | Preserved | Preserved |

The client logic determines the next method by checking if the status code is `SEE_OTHER` (303) or if it's a redirect that requires switching to `GET` [httpx/_client.py:62-91]().

```mermaid
graph TD
    RedirectResponse["httpx.Response"] --> CheckStatus{"status_code"}
    CheckStatus -->|303| ChangeToGET["Method = GET"]
    CheckStatus -->|301,302| MaybeGET["Method = GET (Standard Practice)"]
    CheckStatus -->|307,308| PreserveMethod["Preserve HTTP Method"]
    ChangeToGET --> RemoveBody["Remove Request Body"]
    PreserveMethod --> KeepBody["Keep Request Body"]
```

Sources: [httpx/_status_codes.py:44-52](), [tests/client/test_redirects.py:310-334]()

## Cross-Domain Redirect Security

HTTPX implements security measures for cross-domain redirects, particularly regarding sensitive headers like `Authorization` and `Cookie`.

### Origin Verification

The internal helper `_same_origin(url, other)` is used to determine if a redirect is moving to a different host, scheme, or port [httpx/_client.py:83-91]().

### Authentication Header Stripping

If a redirect is to a different origin, the `Authorization` header is stripped from the next request to prevent credential leakage [tests/client/test_redirects.py:266-299]().

```mermaid
graph TD
    RequestWithAuth["httpx.Request + 'Authorization'"] --> CheckDomain["_same_origin()"]
    CheckDomain -->|True| KeepAuth["Keep Authorization Header"]
    CheckDomain -->|False| StripAuth["Remove Authorization Header"]
    StripAuth --> CrossDomainRequest["Cross-Domain Request"]
    KeepAuth --> SameDomainRequest["Same-Domain Request"]
```

Sources: [httpx/_client.py:83-91](), [tests/client/test_redirects.py:266-299]()

## Error Handling and Limits

HTTPX provides protection against infinite redirect loops and excessive redirects through the `max_redirects` parameter, which defaults to 20 [httpx/_config.py:16-16]().

### TooManyRedirects Exception

Exceeding the limit raises `httpx.TooManyRedirects` [httpx/_exceptions.py:108-110]().

```python
client = httpx.Client(max_redirects=5)
try:
    response = client.get("http://example.com/loop", follow_redirects=True)
except httpx.TooManyRedirects:
    print("Redirect limit reached")
```

### Loop Detection

HTTPX also detects loops where the same URL is requested multiple times in a redirect chain, raising the same exception.

```mermaid
graph TD
    FollowRedirect["Redirect Loop"] --> IncrementCounter["Redirect Count++"]
    IncrementCounter --> CheckLimit{"Count > max_redirects?"}
    CheckLimit -->|Yes| ThrowException["raise TooManyRedirects"]
    CheckLimit -->|No| CheckLoop{"URL in history?"}
    CheckLoop -->|Yes| ThrowException
    CheckLoop -->|No| ContinueRedirect["Send Next Request"]
```

Sources: [httpx/_config.py:16-16](), [httpx/_exceptions.py:108-110](), [tests/client/test_redirects.py:243-264]()

## Stream Handling and Redirects

Streaming responses have special considerations. If a request body is a stream (e.g., a generator) and has been consumed, it cannot be replayed for a redirect unless it is "rewindable."

If a redirect occurs and the stream is not replayable, HTTPX may raise a `StreamConsumed` error or fail to follow the redirect if the body is required for the next request.

Sources: [httpx/_models.py:114-130](), [tests/client/test_redirects.py:352-361]()

---

# Page: Streaming

# Streaming

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_client.py](httpx/_client.py)
- [httpx/_content.py](httpx/_content.py)
- [tests/models/test_requests.py](tests/models/test_requests.py)
- [tests/models/test_responses.py](tests/models/test_responses.py)
- [tests/test_content.py](tests/test_content.py)

</details>



This document covers HTTPX's streaming API for handling large request and response bodies without loading them entirely into memory. Streaming is essential for downloading large files, processing server-sent events, or handling responses that exceed available memory.

## Overview

HTTPX provides two distinct streaming patterns:

1.  **Response streaming**: Consuming response bodies incrementally using iterator methods.
2.  **Request streaming**: Sending request bodies incrementally using generator functions or iterables.

The streaming architecture separates the network I/O layer from the content processing layer, allowing transparent content decoding (gzip, brotli, etc.) while streaming.

### Code Entity Space to Implementation Mapping

The following diagram maps high-level streaming concepts to the specific classes and methods implemented in `httpx`.

```mermaid
graph TB
    subgraph "Client Interface"
        ClientStream["Client.stream() / AsyncClient.stream()"]
        ClientSend["Client.send(stream=True)"]
    end
    
    subgraph "Response Models"
        Response["httpx.Response"]
        State["is_closed, is_stream_consumed"]
    end
    
    subgraph "Iteration API"
        IterRaw["iter_raw() / aiter_raw()"]
        IterBytes["iter_bytes() / aiter_bytes()"]
        IterText["iter_text() / aiter_text()"]
        IterLines["iter_lines() / aiter_lines()"]
    end
    
    subgraph "Stream Implementation"
        BoundStream["BoundSyncStream / BoundAsyncStream"]
        ByteChunker["_decoders.ByteChunker"]
        TextDecoder["_decoders.TextDecoder"]
        LineDecoder["_decoders.LineDecoder"]
    end
    
    ClientStream --> ClientSend
    ClientSend --> Response
    Response --> State
    Response --> IterRaw
    Response --> IterBytes
    Response --> IterText
    Response --> IterLines
    
    IterRaw --> BoundStream
    IterBytes --> ByteChunker
    IterText --> TextDecoder
    IterLines --> LineDecoder
```

Sources: [httpx/_client.py:827-877](), [httpx/_models.py:884-1091](), [httpx/_decoders.py:228-379]()

## The `stream()` Context Manager

The `stream()` method on `Client` and `AsyncClient` returns a context manager that yields a `Response` object in streaming mode. This ensures the response stream is properly closed when exiting the context.

### Synchronous Streaming Flow

```mermaid
sequenceDiagram
    participant User
    participant Client as httpx.Client
    participant Response as httpx.Response
    participant BoundStream as httpx.BoundSyncStream
    
    User->>Client: stream(method, url)
    Client->>Client: _send_single_request(request, stream=True)
    Client->>BoundStream: __init__(stream, response, start_time)
    Client->>Response: set response.stream = BoundStream
    Client-->>User: yield Response
    
    User->>Response: iter_bytes()
    Response->>BoundStream: __iter__()
    BoundStream-->>Response: yield bytes
    Response-->>User: yield chunk
    
    User->>Client: exit context
    Client->>Response: close()
    Response->>BoundStream: close()
    BoundStream->>BoundStream: calculate response.elapsed
```

The `Client.stream()` method is a wrapper around `send()` that forces the `stream=True` parameter.

Sources: [httpx/_client.py:827-877](), [httpx/_client.py:139-161]()

### Async Streaming

The `AsyncClient.stream()` method provides identical functionality for async contexts using `async with` and `aiter_bytes()`/`aiter_text()`/`aiter_lines()`.

Sources: [httpx/_client.py:1616-1664](), [httpx/_client.py:162-183]()

## Response State Management

The `Response` object tracks its lifecycle via properties that prevent invalid I/O operations.

| Property | Description | Implementation |
| :--- | :--- | :--- |
| `is_closed` | True if the underlying stream has been closed. | [httpx/_models.py:543-546]() |
| `is_stream_consumed` | True if the stream has been iterated over. | [httpx/_models.py:548-551]() |
| `elapsed` | The total time taken for the response, set only after closure. | [httpx/_models.py:579-593]() |

### State Transitions

```mermaid
stateDiagram-v2
    [*] --> UNOPENED
    UNOPENED --> OPENED: stream() called
    OPENED --> STREAM_CONSUMED: iter_bytes() / iter_text()
    OPENED --> CLOSED: close() called
    STREAM_CONSUMED --> CLOSED: close() called
    CLOSED --> [*]
```

Sources: [httpx/_models.py:543-551](), [httpx/_client.py:125-137]()

## Response Iteration Methods

HTTPX provides several ways to iterate over the response body, each handling different levels of decoding.

### 1. Raw Bytes: `iter_raw()`
Iterates over the raw bytes directly from the network. No content decompression (gzip, etc.) is applied.
- **Sync**: `iter_raw(chunk_size=None)` [httpx/_models.py:900-918]()
- **Async**: `aiter_raw(chunk_size=None)` [httpx/_models.py:1035-1048]()

### 2. Decoded Bytes: `iter_bytes()`
Applies content decoding (e.g., decompressing gzip) before yielding chunks.
- **Sync**: `iter_bytes(chunk_size=None)` [httpx/_models.py:884-899]()
- **Async**: `aiter_bytes(chunk_size=None)` [httpx/_models.py:1020-1034]()

### 3. Text: `iter_text()`
Applies content decoding and then character decoding (e.g., UTF-8).
- **Sync**: `iter_text(chunk_size=None)` [httpx/_models.py:920-942]()
- **Async**: `aiter_text(chunk_size=None)` [httpx/_models.py:1050-1068]()

### 4. Lines: `iter_lines()`
Yields text line by line, handling universal line endings.
- **Sync**: `iter_lines()` [httpx/_models.py:944-960]()
- **Async**: `aiter_lines()` [httpx/_models.py:1070-1086]()

Sources: [httpx/_models.py:884-1091]()

## Request Streaming

Streaming a request body is achieved by passing an iterable or async iterable to the `content` argument of a request.

### Implementation Details
When an iterable is provided, HTTPX uses `encode_content` in `httpx/_content.py` to determine the stream type.

| Content Type | Stream Class | Header Action |
| :--- | :--- | :--- |
| `Iterable[bytes]` | `IteratorByteStream` | Sets `Transfer-Encoding: chunked` (unless length is known) |
| `AsyncIterable[bytes]` | `AsyncIteratorByteStream` | Sets `Transfer-Encoding: chunked` |
| `bytes` / `str` | `ByteStream` | Sets `Content-Length` |

```mermaid
graph LR
    Input["Request(content=...)"] --> Encoder["_content.encode_content()"]
    Encoder --> SyncIter["IteratorByteStream"]
    Encoder --> AsyncIter["AsyncIteratorByteStream"]
    Encoder --> Raw["ByteStream"]
    
    SyncIter --> Transport["Transport.handle_request()"]
    AsyncIter --> AsyncTransport["AsyncTransport.handle_async_request()"]
```

Sources: [httpx/_content.py:107-134](), [httpx/_content.py:42-90](), [tests/models/test_requests.py:24-51]()

### Non-Replayable Streams
Streaming request bodies are generally "non-replayable". If a request needs to be redirected or re-authenticated, HTTPX cannot automatically rewind the generator/iterator. This will result in a `StreamConsumed` error if a retry is attempted.

Sources: [httpx/_content.py:51-54](), [httpx/_content.py:76-79]()

## The Bound Stream Wrapper

`BoundSyncStream` and `BoundAsyncStream` are internal wrappers used to track the response lifecycle.

- **Initialization**: They take the raw stream, the response object, and a start time. [httpx/_client.py:145-150]()
- **Closure**: When `close()` or `aclose()` is called, they calculate the `elapsed` time and update the response object before closing the underlying transport stream. [httpx/_client.py:156-160](), [httpx/_client.py:179-183]()

Sources: [httpx/_client.py:139-183]()

---

# Page: Core Components

# Core Components

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_models.py](httpx/_models.py)
- [httpx/_types.py](httpx/_types.py)

</details>



This page documents the fundamental data models and structures used throughout HTTPX. These components form the foundation upon which the client API is built and are used consistently across both synchronous and asynchronous interfaces.

The core components include:
- **Request** and **Response** objects for representing HTTP messages
- **URL** for parsing and manipulating URLs
- **Headers** for case-insensitive header handling
- **Cookies** for cookie management  
- **QueryParams** for query string manipulation
- **Content decoders** for transparent decompression
- **Byte streams** for request/response body handling

For information about how clients use these components, see [Client API](#3). For details on the transport layer that processes these objects, see [Transport System](#5).

## Core Component Architecture

The following diagram shows the primary data model classes and their relationships:

```mermaid
graph TB
    subgraph "Request/Response Models"
        Request["Request<br/>httpx._models.Request"]
        Response["Response<br/>httpx._models.Response"]
    end
    
    subgraph "URL Components"
        URL["URL<br/>httpx._urls.URL"]
        QueryParams["QueryParams<br/>httpx._urls.QueryParams"]
    end
    
    subgraph "Header/Cookie Models"
        Headers["Headers<br/>httpx._models.Headers"]
        Cookies["Cookies<br/>httpx._models.Cookies"]
    end
    
    subgraph "Stream Handling"
        SyncByteStream["SyncByteStream<br/>httpx._types.SyncByteStream"]
        AsyncByteStream["AsyncByteStream<br/>httpx._types.AsyncByteStream"]
        ByteStream["ByteStream<br/>httpx._content.ByteStream"]
    end
    
    subgraph "Content Processing"
        ContentDecoder["ContentDecoder<br/>httpx._decoders.ContentDecoder"]
        TextDecoder["TextDecoder<br/>httpx._decoders.TextDecoder"]
    end
    
    Request -->|contains| URL
    Request -->|contains| Headers
    Request -->|uses| SyncByteStream
    Request -->|uses| AsyncByteStream
    
    Response -->|contains| URL
    Response -->|contains| Headers
    Response -->|uses| SyncByteStream
    Response -->|uses| AsyncByteStream
    Response -->|uses| ContentDecoder
    Response -->|uses| TextDecoder
    
    URL -->|contains| QueryParams
    
    Cookies -->|sets headers on| Request
    Cookies -->|extracts from| Response
    
    ByteStream -.implements.-> SyncByteStream
    ByteStream -.implements.-> AsyncByteStream
    
    Response -->|property| Cookies
```

Sources: [httpx/_models.py:51-1279](), [httpx/_urls.py:48-500](), [httpx/_content.py:13-300](), [httpx/_decoders.py:14-400](), [httpx/_types.py:92-115]()

## Request Object

The `Request` class represents an HTTP request with its method, URL, headers, and body content. Requests are immutable once constructed.

### Request Structure

| Property | Type | Description |
|----------|------|-------------|
| `method` | `str` | HTTP method (GET, POST, etc.) - automatically uppercased |
| `url` | `URL` | Parsed URL object |
| `headers` | `Headers` | Case-insensitive HTTP headers |
| `content` | `bytes` | Request body content (after reading) |
| `stream` | `SyncByteStream` \| `AsyncByteStream` | Request body stream |
| `extensions` | `dict` | Request metadata (e.g., timeout configuration) |

### Request Construction Flow

```mermaid
flowchart TD
    Init["Request.__init__()<br/>httpx._models.Request"]
    
    ParseURL["Parse URL<br/>URL(url, params=params)"]
    CreateHeaders["Create Headers<br/>Headers(headers)"]
    SetCookies["Set Cookie Header<br/>Cookies.set_cookie_header()"]
    
    EncodeRequest["encode_request()<br/>httpx._content.encode_request"]
    PrepareHeaders["_prepare()<br/>Auto-add Host, Content-Length"]
    
    LoadStream["ByteStream.read()<br/>Load into memory"]
    
    Init --> ParseURL
    Init --> CreateHeaders
    Init --> SetCookies
    
    ParseURL --> EncodeRequest
    CreateHeaders --> EncodeRequest
    
    EncodeRequest --> PrepareHeaders
    PrepareHeaders --> LoadStream
    
    LoadStream --> Ready["Request Ready"]
```

Sources: [httpx/_models.py:382-513]()

### Request Body Encoding

The request body is encoded based on the arguments provided:

- **`content`** - Raw bytes or string passed directly [httpx/_models.py:406-407]()
- **`data`** - Form-encoded as `application/x-www-form-urlencoded` [httpx/_models.py:408-409]()
- **`files`** - Multipart form data as `multipart/form-data` [httpx/_models.py:410-411]()
- **`json`** - JSON-encoded with `Content-Type: application/json` [httpx/_models.py:412-413]()
- **`stream`** - Custom byte stream (bypasses automatic encoding) [httpx/_models.py:414-415]()

The `encode_request()` function in `httpx._content` handles this encoding and returns appropriate headers and a byte stream [httpx/_content.py:143-242]().

For details, see [Request Objects](#4.1).

## Response Object

The `Response` class represents an HTTP response with status code, headers, body content, and metadata. Responses support both immediate content access and streaming consumption.

### Response Structure

| Property | Type | Description |
|----------|------|-------------|
| `status_code` | `int` | HTTP status code (e.g., 200, 404) |
| `headers` | `Headers` | Case-insensitive response headers |
| `content` | `bytes` | Decoded response body (raises if not read) |
| `text` | `str` | Decoded text content with charset detection |
| `encoding` | `str \| None` | Character encoding for text decoding |
| `request` | `Request` | Associated request object |
| `history` | `list[Response]` | Previous responses in redirect chain |
| `is_closed` | `bool` | Whether response stream is closed |
| `is_stream_consumed` | `bool` | Whether stream has been read |
| `elapsed` | `timedelta` | Request/response cycle duration |

### Response State Diagram

```mermaid
stateDiagram-v2
    [*] --> Created: Response()
    
    Created --> Streaming: iter_bytes()<br/>iter_raw()
    Created --> FullyRead: read()
    
    Streaming --> StreamConsumed: Stream exhausted
    StreamConsumed --> Closed: close()<br/>auto-close
    
    FullyRead --> Closed: close()<br/>auto-close
    
    Closed --> [*]
    
    note right of Created
        is_closed = False
        is_stream_consumed = False
    end note
    
    note right of Streaming
        is_closed = False
        is_stream_consumed = True
    end note
    
    note right of Closed
        is_closed = True
    end note
```

Sources: [httpx/_models.py:515-877](), [httpx/_models.py:935-960]()

### Response Content Access

The `Response` class provides multiple ways to access content:

**Properties (require full read):**
- `response.content` - Raw bytes [httpx/_models.py:636-650]()
- `response.text` - Decoded text string [httpx/_models.py:652-671]()
- `response.json()` - Parsed JSON [httpx/_models.py:689-697]()

**Streaming methods:**
- `response.iter_bytes(chunk_size)` - Decoded byte chunks [httpx/_models.py:876-897]()
- `response.iter_text(chunk_size)` - Decoded text chunks [httpx/_models.py:899-918]()
- `response.iter_lines()` - Text lines (without newlines) [httpx/_models.py:920-933]()
- `response.iter_raw(chunk_size)` - Raw bytes (before decoding) [httpx/_models.py:935-960]()

For details, see [Response Objects](#4.2).

## URL Class

The `URL` class provides RFC3986-compliant URL parsing, validation, and manipulation with support for IDNA encoding and IPv6 addresses.

### URL Component Breakdown

```mermaid
graph LR
    URLString["https://user:pass@example.com:8080/path/to/page?key=value#section"]
    
    URLString --> scheme["scheme: 'https'"]
    URLString --> userinfo["userinfo: b'user:pass'"]
    URLString --> host["host: 'example.com'"]
    URLString --> port["port: 8080"]
    URLString --> path["path: '/path/to/page'"]
    URLString --> query["query: b'key=value'"]
    URLString --> fragment["fragment: 'section'"]
    
    userinfo --> username["username: 'user'"]
    userinfo --> password["password: 'pass'"]
    
    query --> params["params:<br/>QueryParams"]
```

Sources: [httpx/_urls.py:100-400]()

For details, see [URL Handling](#4.3).

## Headers and Cookies

### Headers Class

The `Headers` class implements a case-insensitive, multi-value dictionary for HTTP headers [httpx/_models.py:139-142](). It maintains insertion order and supports multiple values for the same header name via `get_list()` [httpx/_models.py:246-261]().

### Cookies Class

The `Cookies` class wraps Python's `http.cookiejar.CookieJar` to provide a simpler dictionary-like interface for cookie management [httpx/_models.py:1079-1082]().

For details, see [Headers and Cookies](#4.4).

## Query Parameters

The `QueryParams` class provides an immutable multi-dict interface for URL query parameters [httpx/_urls.py:450-453](). All modification operations like `set()`, `add()`, or `remove()` return new instances rather than modifying in place [httpx/_urls.py:533-568]().

For details, see [Query Parameters](#4.5).

## Content Encoding and Decoding

HTTPX automatically handles content decompression (gzip, deflate, brotli, zstd) through a series of `ContentDecoder` implementations [httpx/_decoders.py:14-23](). Character encoding detection for `response.text` is handled by parsing the `Content-Type` header or falling back to default encodings [httpx/_models.py:699-722]().

For details, see [Content Encoding and Decoding](#4.6).

## Multipart Form Data

Multipart form data encoding is used when the `files` parameter is passed to a request. This is handled by `httpx._multipart`, which generates the appropriate boundaries and stream [httpx/_models.py:33](), [httpx/_content.py:177-184]().

For details, see [Multipart Form Data](#4.7).

## Byte Streams

Byte streams provide the abstraction for reading request and response bodies. They support both synchronous and asynchronous iteration via `SyncByteStream` and `AsyncByteStream` [httpx/_types.py:92-115]().

Sources: [httpx/_types.py:92-115](), [httpx/_content.py:50-150]()

---

# Page: Request Objects

# Request Objects

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_models.py](httpx/_models.py)

</details>



Request objects are the fundamental data structures that encapsulate HTTP request information in `httpx`. They handle content encoding, stream management, and provide both synchronous and asynchronous interfaces for request data access. This page covers the `Request` class implementation, content encoding mechanisms, and stream handling patterns.

## Request Object Structure

The `Request` class serves as the primary container for HTTP request data, combining URL, headers, method, and body content into a unified interface.

### Core Request Architecture

```mermaid
classDiagram
    class Request {
        +string method
        +URL url
        +Headers headers
        +dict extensions
        +SyncByteStream|AsyncByteStream stream
        +bytes content
        +__init__(method, url, **kwargs)
        +read() bytes
        +aread() bytes
        +_prepare(default_headers)
    }
    
    class Headers {
        +list _list
        +string encoding
        +__getitem__(key)
        +__setitem__(key, value)
        +update(headers)
    }
    
    class URL {
        +string scheme
        +string host
        +string path
        +QueryParams params
    }
    
    class ByteStream {
        +bytes _stream
        +__iter__()
        +__aiter__()
    }
    
    class IteratorByteStream {
        +Iterable _stream
        +bool _is_stream_consumed
        +__iter__()
    }
    
    class AsyncIteratorByteStream {
        +AsyncIterable _stream
        +bool _is_stream_consumed
        +__aiter__()
    }
    
    Request --> Headers
    Request --> URL
    Request --> ByteStream
    Request --> IteratorByteStream
    Request --> AsyncIteratorByteStream
```

Sources: [httpx/_models.py:382-440](), [httpx/_content.py:31-105]()

### Request Initialization Parameters

The `Request` constructor accepts multiple parameter types for flexible request creation:

| Parameter | Type | Purpose |
|-----------|------|---------|
| `method` | `str` | HTTP method (GET, POST, etc.) |
| `url` | `URL \| str` | Request URL, merged with params if provided |
| `headers` | `HeaderTypes` | HTTP headers as dict, list of tuples, or Headers object |
| `cookies` | `CookieTypes` | Cookies to include in request |
| `content` | `RequestContent` | Raw request body content |
| `data` | `RequestData` | Form data for URL encoding |
| `files` | `RequestFiles` | Files for multipart encoding |
| `json` | `Any` | JSON-serializable data |
| `stream` | `SyncByteStream \| AsyncByteStream` | Pre-built stream object |
| `extensions` | `RequestExtensions` | Transport-specific metadata |

Sources: [httpx/_models.py:383-397]()

## Request Building Process

Request building involves content encoding, header preparation, and stream creation. The process varies depending on the input parameters provided.

### Content Encoding Flow

```mermaid
flowchart TD
    A["Request.__init__()"] --> B{"stream provided?"}
    B -->|Yes| C["Use provided stream"]
    B -->|No| D["encode_request()"]
    
    D --> E{"content type?"}
    E -->|content| F["encode_content()"]
    E -->|files| G["encode_multipart_data()"]
    E -->|data| H["encode_urlencoded_data()"]
    E -->|json| I["encode_json()"]
    E -->|none| J["ByteStream(b'')"]
    
    F --> K["headers, stream"]
    G --> K
    H --> K
    I --> K
    J --> K
    
    K --> L["_prepare(headers)"]
    L --> M["Auto-add Host, Content-Length"]
    M --> N["Request ready"]
    C --> N
```

Sources: [httpx/_models.py:406-440](), [httpx/_content.py:186-218]()

### Header Preparation

The `_prepare()` method automatically adds required headers based on the request configuration:

```mermaid
flowchart LR
    A["_prepare(default_headers)"] --> B["Merge default headers"]
    B --> C{"Has Host header?"}
    C -->|No| D["Add Host from URL"]
    C -->|Yes| E{"Has Content-Length?"}
    D --> E
    E -->|No| F{"Method needs body?"}
    F -->|POST/PUT/PATCH| G["Add Content-Length: 0"]
    F -->|Other| H["Headers complete"]
    E -->|Yes| H
    G --> H
```

Sources: [httpx/_models.py:441-461]()

## Content Encoding Mechanisms

`httpx` supports multiple content encoding strategies through the `encode_request()` function and specialized encoding functions.

### Encoding Strategy Selection

The content encoding strategy is determined by the parameters provided to the `Request` constructor:

| Input Parameter | Encoding Function | Headers Set | Stream Type |
|----------------|-------------------|-------------|-------------|
| `content=bytes` | `encode_content()` | `Content-Length` | `ByteStream` |
| `content=Iterator` | `encode_content()` | `Transfer-Encoding: chunked` | `IteratorByteStream` |
| `data=dict` | `encode_urlencoded_data()` | `Content-Type: application/x-www-form-urlencoded` | `ByteStream` |
| `files=dict` | `encode_multipart_data()` | `Content-Type: multipart/form-data` | `MultipartStream` |
| `json=object` | `encode_json()` | `Content-Type: application/json` | `ByteStream` |

Sources: [httpx/_content.py:186-218]()

### Stream Type Hierarchy

```mermaid
classDiagram
    class SyncByteStream {
        <<interface>>
        +__iter__() Iterator[bytes]
    }
    
    class AsyncByteStream {
        <<interface>>
        +__aiter__() AsyncIterator[bytes]
    }
    
    class ByteStream {
        +bytes _stream
        +__iter__()
        +__aiter__()
    }
    
    class IteratorByteStream {
        +Iterable _stream
        +bool _is_stream_consumed
        +bool _is_generator
        +__iter__()
    }
    
    class AsyncIteratorByteStream {
        +AsyncIterable _stream
        +bool _is_stream_consumed
        +bool _is_generator
        +__aiter__()
    }
    
    class UnattachedStream {
        +__iter__() raises StreamClosed
        +__aiter__() raises StreamClosed
    }
    
    SyncByteStream <|-- ByteStream
    AsyncByteStream <|-- ByteStream
    SyncByteStream <|-- IteratorByteStream
    AsyncByteStream <|-- AsyncIteratorByteStream
    SyncByteStream <|-- UnattachedStream
    AsyncByteStream <|-- UnattachedStream
```

Sources: [httpx/_content.py:31-105](), [httpx/_types.py]()

## Stream Handling and Consumption

Request streams support both synchronous and asynchronous iteration patterns, with built-in protection against multiple consumption of generator-based streams.

### Stream Consumption Patterns

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Request
    participant S as Stream
    
    Note over C,S: Synchronous Pattern
    C->>R: request.read()
    R->>S: list(stream)
    S-->>R: bytes chunks
    R->>R: _content = b"".join(chunks)
    R-->>C: content bytes
    
    Note over C,S: Asynchronous Pattern  
    C->>R: await request.aread()
    R->>S: [part async for part in stream]
    S-->>R: async bytes chunks
    R->>R: _content = b"".join(chunks)
    R-->>C: content bytes
    
    Note over C,S: Stream Protection
    C->>R: request.read() (second call)
    R-->>C: cached _content (no re-read)
```

Sources: [httpx/_models.py:468-495]()

### Stream State Management

Request streams implement consumption tracking to prevent issues with non-replayable streams:

- **Generator Streams**: Marked as consumed after first iteration in `IteratorByteStream` or `AsyncIteratorByteStream`, raising `StreamConsumed` on subsequent access [httpx/_content.py:61-64]().
- **Cached Content**: Once read via `read()` or `aread()`, content is cached in the `_content` attribute [httpx/_models.py:479-495]().
- **Stream Replacement**: After reading, the stream is replaced with a `ByteStream` containing the full content to ensure replayability [httpx/_models.py:478]().

Sources: [httpx/_content.py:42-89](), [httpx/_models.py:468-495]()

## Request Lifecycle Integration

### Client Request Building

The `Client.build_request()` and `AsyncClient.build_request()` methods coordinate request creation with client-level configuration:

```mermaid
flowchart TD
    A["client.build_request()"] --> B["_merge_url()"]
    B --> C["_merge_headers()"]
    C --> D["_merge_cookies()"]
    D --> E["_merge_queryparams()"]
    E --> F["Request.__init__()"]
    F --> G["encode_request()"]
    G --> H["_prepare()"]
    H --> I["Request ready"]
```

Sources: [httpx/_client.py:340-389]()

### Transport Integration

Requests interface with the transport layer through their stream and extensions:

- **Stream Interface**: Transports consume request streams during transmission by iterating over `request.stream` [httpx/_transports/default.py:230-234]().
- **Extensions**: Carry transport-specific metadata like timeouts and authentication [httpx/_models.py:397]().
- **Stream Type Checking**: Transports verify sync/async compatibility before processing.

Sources: [httpx/_client.py:1001-1034]()

### Serialization Support

Request objects support pickle serialization with stream state preservation:

- **Serializable Fields**: Method, URL, headers, and content (if already read) are preserved [httpx/_models.py:501-507]().
- **Excluded Fields**: The active `stream` and `extensions` are excluded from serialization [httpx/_models.py:505]().
- **Restoration**: Deserialized requests use `UnattachedStream` to prevent invalid operations if the original stream was not read before pickling [httpx/_models.py:512]().

Sources: [httpx/_models.py:501-513]()

---

# Page: Response Objects

# Response Objects

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_models.py](httpx/_models.py)
- [httpx/_status_codes.py](httpx/_status_codes.py)
- [tests/models/test_requests.py](tests/models/test_requests.py)
- [tests/models/test_responses.py](tests/models/test_responses.py)
- [tests/test_status_codes.py](tests/test_status_codes.py)

</details>



Response objects represent HTTP responses received from servers or created programmatically for testing. The `httpx.Response` class provides access to response status, headers, body content, and streaming capabilities, with support for both synchronous and asynchronous operations.

For information about making requests that produce responses, see [Making Requests](#2.1). For information about streaming responses during the request lifecycle, see [Streaming](#3.5).

**Sources:** [httpx/_models.py:51-51](), [httpx/_models.py:515-1080]()

## Response Structure and Relationships

The following diagram shows the core structure of a Response object and its relationships with other components:

```mermaid
graph TB
    subgraph "Response Object [httpx._models.Response]"
        Response["Response"]
        StatusCode["status_code: int"]
        Headers["headers: Headers"]
        Stream["stream: ByteStream"]
        Request["_request: Request | None"]
        Extensions["extensions: dict"]
        History["history: list[Response]"]
        NextRequest["next_request: Request | None"]
        
        Response --> StatusCode
        Response --> Headers
        Response --> Stream
        Response --> Request
        Response --> Extensions
        Response --> History
        Response --> NextRequest
    end
    
    subgraph "State Properties"
        IsClosed["is_closed: bool"]
        IsStreamConsumed["is_stream_consumed: bool"]
        Elapsed["_elapsed: timedelta"]
        
        Response --> IsClosed
        Response --> IsStreamConsumed
        Response --> Elapsed
    end
    
    subgraph "Cached Content"
        Content["_content: bytes"]
        Text["_text: str"]
        Encoding["_encoding: str"]
        
        Response -.caches.-> Content
        Response -.caches.-> Text
        Response -.caches.-> Encoding
    end
    
    subgraph "Content Processing"
        ContentDecoder["ContentDecoder"]
        TextDecoder["TextDecoder"]
        LineDecoder["LineDecoder"]
        
        Stream --> ContentDecoder
        ContentDecoder --> TextDecoder
        TextDecoder --> LineDecoder
    end
```

**Sources:** [httpx/_models.py:515-594](), [httpx/_models.py:636-698]()

## Creating Response Instances

Response objects are typically created by the client during request execution, but can also be instantiated directly for testing purposes.

### Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `status_code` | `int` | HTTP status code (e.g., 200, 404, 500) |
| `headers` | `HeaderTypes \| None` | Response headers as dict, list of tuples, or Headers instance |
| `content` | `ResponseContent \| None` | Response body as bytes or string |
| `text` | `str \| None` | Response body as text (automatically sets Content-Type) |
| `html` | `str \| None` | HTML response body (sets Content-Type to text/html) |
| `json` | `Any` | JSON-serializable object (sets Content-Type to application/json) |
| `stream` | `SyncByteStream \| AsyncByteStream \| None` | Streaming response body |
| `request` | `Request \| None` | Associated request instance |
| `extensions` | `ResponseExtensions \| None` | Protocol-specific metadata |
| `history` | `list[Response] \| None` | Previous responses in redirect chain |
| `default_encoding` | `str \| Callable[[bytes], str]` | Default encoding or auto-detect function |

**Sources:** [httpx/_models.py:516-570]()

### Example Usage

```python
# Created by client (typical usage)
response = client.get("https://example.org")

# Created for testing
response = httpx.Response(
    200,
    content=b"Hello, world!",
    headers={"Content-Type": "text/plain"},
)

# Created with convenience parameters
response = httpx.Response(200, text="Hello, world!")
response = httpx.Response(200, json={"message": "success"})
response = httpx.Response(200, html="<html>...</html>")
```

**Sources:** [tests/models/test_responses.py:31-89]()

## Status Code and Status Properties

### Basic Status Information

The response status code and reason phrase are accessed through properties:

```python
response.status_code  # int: 200, 404, 500, etc.
response.reason_phrase  # str: "OK", "Not Found", "Internal Server Error"
response.http_version  # str: "HTTP/1.1", "HTTP/2", etc.
```

**Sources:** [httpx/_models.py:610-627](), [httpx/_status_codes.py:39-43]()

### Status Code Category Properties

Response provides boolean properties to check the category of status codes via the `codes` enum:

| Property | Status Range | Description |
|----------|--------------|-------------|
| `is_informational` | 100-199 | Informational responses (1xx) |
| `is_success` | 200-299 | Successful responses (2xx) |
| `is_redirect` | 300-399 | Redirection messages (3xx) |
| `is_client_error` | 400-499 | Client error responses (4xx) |
| `is_server_error` | 500-599 | Server error responses (5xx) |
| `is_error` | 400-599 | Any error (4xx or 5xx) |

**Sources:** [httpx/_models.py:781-818](), [httpx/_status_codes.py:45-85]()

### Redirect Detection

```python
response.is_redirect  # True for any 3xx status
response.has_redirect_location  # True if has valid Location header
```

**Sources:** [httpx/_models.py:807-818]()

### Raising Exceptions for Error Status

The `raise_for_status()` method raises `HTTPStatusError` for non-2xx responses:

```python
try:
    response = client.get("https://example.org/api")
    response.raise_for_status()  # Raises if not 2xx
except httpx.HTTPStatusError as exc:
    print(f"Error: {exc.response.status_code}")
```

**Sources:** [httpx/_models.py:854-889](), [httpx/_exceptions.py:26-26]()

## Content Access

### Raw Byte Content

The `content` property provides the complete response body as bytes:

```python
content = response.content  # bytes
```

This property is cached after first access. Attempting to access `content` before reading a streaming response raises `ResponseNotRead`.

**Sources:** [httpx/_models.py:636-639](), [httpx/_exceptions.py:28-28]()

### Reading Response Body

For streaming responses, the body must be explicitly read:

```python
# Synchronous
content = response.read()  # bytes

# Asynchronous
content = await response.aread()  # bytes
```

After reading, the response is automatically closed and `is_closed` becomes `True`.

**Sources:** [httpx/_models.py:891-940]()

## Content Decoding Pipeline

The following diagram shows how response content flows through the decoding pipeline:

```mermaid
graph LR
    subgraph "Transport Layer"
        RawBytes["Raw Bytes<br/>from Network"]
    end
    
    subgraph "Response Stream [httpx._content.ByteStream]"
        ByteStream["SyncByteStream /<br/>AsyncByteStream"]
    end
    
    subgraph "Content Decoding [httpx._decoders.ContentDecoder]"
        ContentDecoder["ContentDecoder"]
        GZip["GZipDecoder"]
        Deflate["DeflateDecoder"]
        Brotli["BrotliDecoder"]
        Zstd["ZStandardDecoder"]
        Multi["MultiDecoder"]
        
        ContentDecoder -.subclass.-> GZip
        ContentDecoder -.subclass.-> Deflate
        ContentDecoder -.subclass.-> Brotli
        ContentDecoder -.subclass.-> Zstd
        ContentDecoder -.subclass.-> Multi
    end
    
    subgraph "Byte Processing"
        ByteChunker["ByteChunker [httpx._decoders.ByteChunker]"]
        DecodedBytes["Decoded Bytes"]
    end
    
    subgraph "Text Processing"
        TextDecoder["TextDecoder [httpx._decoders.TextDecoder]"]
        TextChunker["TextChunker [httpx._decoders.TextChunker]"]
        LineDecoder["LineDecoder [httpx._decoders.LineDecoder]"]
        DecodedText["Text / Lines"]
    end
    
    RawBytes --> ByteStream
    ByteStream --> ContentDecoder
    ContentDecoder --> ByteChunker
    ByteChunker --> DecodedBytes
    
    DecodedBytes --> TextDecoder
    TextDecoder --> TextChunker
    TextChunker --> DecodedText
    
    TextDecoder --> LineDecoder
    LineDecoder --> DecodedText
```

**Sources:** [httpx/_decoders.py:36-394](), [httpx/_models.py:699-724]()

### Automatic Content Decompression

HTTPX automatically decompresses response content based on the `Content-Encoding` header:

| Encoding | Decoder | Optional Dependency |
|----------|---------|---------------------|
| `gzip` | `GZipDecoder` | Built-in (zlib) |
| `deflate` | `DeflateDecoder` | Built-in (zlib) |
| `br` | `BrotliDecoder` | `httpx[brotli]` |
| `zstd` | `ZStandardDecoder` | `httpx[zstd]` |
| `identity` | `IdentityDecoder` | N/A (no-op) |

**Sources:** [httpx/_decoders.py:381-394](), [httpx/_models.py:699-724]()

## Text and Encoding

### Text Property

The `text` property decodes the response body to a string:

```python
text = response.text  # str
```

**Sources:** [httpx/_models.py:642-650]()

### Encoding Detection

The `encoding` property determines the character encoding. It checks the `Content-Type` header using `_parse_content_type_charset`.

```mermaid
graph TD
    Start["Determine Encoding"]
    CheckCached{"Encoding<br/>cached?"}
    UseCached["Use cached encoding"]
    CheckCharset{"charset in<br/>Content-Type?"}
    UseCharset["Use charset encoding"]
    CheckValid{"Valid<br/>encoding?"}
    CheckDefault{"default_encoding<br/>type?"}
    IsString["String: Use as-is"]
    IsCallable["Callable: Auto-detect"]
    FallbackUTF8["Fallback to utf-8"]
    Done["Return encoding"]
    
    Start --> CheckCached
    CheckCached -->|Yes| UseCached
    CheckCached -->|No| CheckCharset
    CheckCharset -->|Yes| UseCharset
    UseCharset --> CheckValid
    CheckCharset -->|No| CheckDefault
    CheckValid -->|Valid| Done
    CheckValid -->|Invalid| CheckDefault
    CheckDefault -->|String| IsString
    CheckDefault -->|Callable| IsCallable
    CheckDefault -->|None| FallbackUTF8
    IsString --> Done
    IsCallable --> Done
    FallbackUTF8 --> Done
    UseCached --> Done
```

**Sources:** [httpx/_models.py:85-90](), [httpx/_models.py:653-687](), [httpx/_models.py:689-697]()

## JSON Parsing

The `json()` method parses JSON response content using the standard `json` library:

```python
data = response.json()  # Any (dict, list, etc.)
```

**Sources:** [httpx/_models.py:6-6](), [httpx/_models.py:942-1003]()

## Streaming Methods

Response objects provide multiple streaming methods for memory-efficient processing.

| Method | Content Decoding | Text Decoding | Line Splitting |
|--------|------------------|---------------|----------------|
| `iter_raw()` | ❌ | ❌ | ❌ |
| `iter_bytes()` | ✅ | ❌ | ❌ |
| `iter_text()` | ✅ | ✅ | ❌ |
| `iter_lines()` | ✅ | ✅ | ✅ |

**Sources:** [httpx/_models.py:1005-1311]()

## Response State Management

```mermaid
stateDiagram-v2
    [*] --> Created: Response()
    
    Created --> StreamOpen: stream != None
    Created --> ContentLoaded: content/text/json provided
    
    StreamOpen --> StreamConsumed: iter_*() consumes stream
    StreamOpen --> ContentRead: read() / aread()
    StreamOpen --> Closed: close() / aclose()
    
    StreamConsumed --> Closed: close() / aclose()
    ContentRead --> Closed: Automatic
    ContentLoaded --> Closed: Automatic
    
    Closed --> [*]
    
    note right of StreamOpen
        is_closed = False
        is_stream_consumed = False
    end note
```

**Sources:** [httpx/_models.py:543-544](), [httpx/_models.py:891-940](), [httpx/_models.py:1313-1360]()

### State Properties

| Property | Type | Description |
|----------|------|-------------|
| `is_closed` | `bool` | Whether the response stream has been closed |
| `is_stream_consumed` | `bool` | Whether the stream has been fully consumed |

**Sources:** [httpx/_models.py:543-544](), [httpx/_exceptions.py:29-30]()

## Timing Information

The `elapsed` property provides the total time taken for the request/response cycle:

```python
response.elapsed  # datetime.timedelta
```

**Sources:** [httpx/_models.py:579-593]()

## Link Headers

The `links` property parses RFC 8288 Link headers using `_parse_header_links`:

```python
response.links  # dict[str, dict[str, str]]
```

**Sources:** [httpx/_models.py:93-127](), [httpx/_models.py:1383-1392]()

## Serialization

Response objects support pickle serialization:

```python
import pickle
data = pickle.dumps(response)
restored = pickle.loads(data)
```

**Sources:** [httpx/_models.py:1394-1412](), [tests/models/test_responses.py:958-994]()

---

# Page: URL Handling

# URL Handling

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_urlparse.py](httpx/_urlparse.py)
- [httpx/_urls.py](httpx/_urls.py)
- [tests/models/test_url.py](tests/models/test_url.py)
- [tests/models/test_whatwg.py](tests/models/test_whatwg.py)
- [tests/models/whatwg.json](tests/models/whatwg.json)

</details>



## Purpose and Scope

This document describes how HTTPX parses, validates, normalizes, and manipulates URLs. URL handling is a core component in HTTPX's architecture that provides robust URL processing capabilities, including support for URL validation, internationalized domain names (IDNA), IPv4/IPv6 addresses, and comprehensive operations for URL modification.

URL handling in HTTPX follows the standards defined in RFC 3986 and the WHATWG URL specification, with additional functionality to support the specific needs of an HTTP client. For information about how query parameters are processed separately, see [Query Parameters](#4.5).

Sources: [httpx/_urlparse.py:1-17]()

## URL Class Overview

The `URL` class in [httpx/_urls.py:15]() provides an object-oriented interface for working with URLs. It serves as a normalized, IDNA-supporting URL representation that wraps the lower-level `urlparse` function from [httpx/_urlparse.py]().

### URL Class Structure

```mermaid
classDiagram
    class URL {
        -_uri_reference: ParseResult
        +scheme: str
        +raw_scheme: bytes
        +userinfo: bytes
        +username: str
        +password: str
        +host: str
        +raw_host: bytes
        +port: int|None
        +netloc: bytes
        +path: str
        +query: bytes
        +params: QueryParams
        +raw_path: bytes
        +fragment: str
        +is_absolute_url: bool
        +is_relative_url: bool
        +__init__(url, **kwargs)
        +copy_with(**kwargs): URL
        +join(url): URL
        +copy_set_param(key, value): URL
        +copy_add_param(key, value): URL
        +copy_remove_param(key): URL
        +copy_merge_params(params): URL
    }
    
    class ParseResult {
        +scheme: str
        +userinfo: str
        +host: str
        +port: int | None
        +path: str
        +query: str | None
        +fragment: str | None
        +authority: str
        +netloc: str
        +copy_with(**kwargs): ParseResult
    }
    
    URL --> ParseResult : "_uri_reference"
```

Sources: [httpx/_urls.py:15-125](), [httpx/_urlparse.py:158-211](), [tests/models/test_url.py:8-21]()

The `URL` class stores a `ParseResult` internally and provides properties for accessing different components of a URL, as well as methods for manipulating URLs. It performs automatic normalization, percent-encoding, and validation of URL components through the `urlparse` function.

## URL Components and Structure

A URL in HTTPX is broken down into the following components, following RFC 3986:

```mermaid
graph TD
    subgraph "URL Components"
        URL["URL: https://username:password@example.com:123/path/to/resource?name=value#section"]
        Scheme["scheme: https"]
        Authority["authority: username:password@example.com:123"]
        Path["path: /path/to/resource"]
        Query["query: name=value"]
        Fragment["fragment: section"]
        
        subgraph "Authority Components"
            Userinfo["userinfo: username:password"]
            Host["host: example.com"]
            Port["port: 123"]
        end
    end
    
    URL --> Scheme
    URL --> Authority
    URL --> Path
    URL --> Query
    URL --> Fragment
    
    Authority --> Userinfo
    Authority --> Host
    Authority --> Port
```

Sources: [httpx/_urlparse.py:102-105](), [httpx/_urlparse.py:122-125](), [tests/models/test_url.py:24-37]()

### Component Types and Rules

URL components are subject to specific validation and normalization rules:

1.  **Scheme**: Must start with a letter and can only contain letters, digits, plus, period, or hyphen. [httpx/_urlparse.py:114]()
2.  **Userinfo**: Represents username and password, percent-encoded when necessary. [httpx/_urlparse.py:129]()
3.  **Host**: Can be a domain name, IPv4 address, or IPv6 address (enclosed in square brackets). [httpx/_urlparse.py:130-131]()
4.  **Port**: Must be a valid integer; normalized to `None` if it matches the default for the scheme. [httpx/_urlparse.py:395-419]()
5.  **Path**: Must be empty or start with a forward slash for absolute URLs. [httpx/_urlparse.py:422-444]()
6.  **Query**: Contains the query parameters, may be `None` to indicate absence, or empty string for a bare `?`. [httpx/_urlparse.py:8-9]()
7.  **Fragment**: Contains the fragment identifier, may be `None` to indicate absence. [httpx/_urlparse.py:165]()

Sources: [httpx/_urlparse.py:32-98](), [tests/models/test_url.py:74-140]()

## URL Parsing and Validation

HTTPX implements its own URL parsing system in [httpx/_urlparse.py]() rather than relying on Python's standard library `urlparse`. The custom implementation provides more complete URL validation, proper handling of empty vs absent query strings, and support for IDNA hostnames.

### URL Parsing Architecture

```mermaid
flowchart TD
    URLClass["URL.__init__()"] --> CheckType{"isinstance(url, str)?"}
    CheckType -- "Yes" --> CallUrlparse["urlparse(url, **kwargs)"]
    CheckType -- "No" --> CopyWith["url._uri_reference.copy_with(**kwargs)"]
    
    CallUrlparse --> URLRegex["URL_REGEX.match(url)\nExtract components"]
    URLRegex --> AuthorityRegex["AUTHORITY_REGEX.match(authority)\nExtract userinfo, host, port"]
    AuthorityRegex --> ValidateComponents["Validate and Normalize\n- encode_host()\n- normalize_port()\n- validate_path()\n- normalize_path()"]
    ValidateComponents --> ParseResultNode["ParseResult(...)"]
    
    CopyWith --> ParseResultNode
    ParseResultNode --> URLInstance["URL instance with\n_uri_reference"]
    
    subgraph "encode_host() Function"
        HostInput["Host String"] --> HostType{"Host Type?"}
        HostType -- "IPv4_STYLE_HOSTNAME" --> IPv4Valid["ipaddress.IPv4Address()"]
        HostType -- "IPv6_STYLE_HOSTNAME" --> IPv6Valid["ipaddress.IPv6Address()"]
        HostType -- "ASCII" --> QuoteHost["quote() with SUB_DELIMS"]
        HostType -- "Unicode" --> IDNAEncode["idna.encode().decode('ascii')"]
    end
    
    ValidateComponents --> HostInput
```

Sources: [httpx/_urls.py:116-124](), [httpx/_urlparse.py:213-345](), [httpx/_urlparse.py:348-392](), [httpx/_urlparse.py:106-134]()

### Core Parsing Functions

The parsing process uses several key components:

| Component | Purpose | Source |
|-----------|---------|---------|
| `URL_REGEX` | Extracts scheme, authority, path, query, fragment | [httpx/_urlparse.py:106-120]() |
| `AUTHORITY_REGEX` | Parses authority into userinfo, host, port | [httpx/_urlparse.py:125-134]() |
| `urlparse()` | Main parsing function returning `ParseResult` | [httpx/_urlparse.py:213-345]() |
| `encode_host()` | Validates and encodes hostnames (IPv4/IPv6/IDNA) | [httpx/_urlparse.py:348-392]() |
| `normalize_port()` | Validates ports and applies scheme defaults | [httpx/_urlparse.py:395-419]() |

Sources: [httpx/_urlparse.py:106-419]()

### Validation Rules

HTTPX strictly validates URLs in the `urlparse()` function to ensure they conform to standards:

| Validation Rule | Implementation | Constants/Functions |
|-----------------|----------------|-------------------|
| Maximum URL length | 65,536 characters | `MAX_URL_LENGTH` [httpx/_urlparse.py:29]() |
| Printable characters only | Rejects ASCII control chars | [httpx/_urlparse.py:223-229]() |
| IPv4 address validation | `ipaddress.IPv4Address()` | `IPv4_STYLE_HOSTNAME` [httpx/_urlparse.py:154]() |
| IPv6 address validation | `ipaddress.IPv6Address()` | `IPv6_STYLE_HOSTNAME` [httpx/_urlparse.py:155]() |
| IDNA hostname encoding | `idna.encode()` | [httpx/_urlparse.py:389-392]() |
| Component regex validation | Each component matched against regex | `COMPONENT_REGEX` [httpx/_urlparse.py:140-149]() |
| Path validation rules | Based on scheme/authority presence | `validate_path()` [httpx/_urlparse.py:422-444]() |

Sources: [httpx/_urlparse.py:217-229](), [httpx/_urlparse.py:284-286](), [httpx/_urlparse.py:352-392](), [tests/models/test_url.py:343-377]()

## URL Normalization

Normalization is the process of standardizing URLs to a canonical form. HTTPX performs several normalization operations in the `urlparse()` function:

### Normalization Functions and Rules

```mermaid
flowchart TD
    InputComponents["URL Components"] --> SchemeNorm["parsed_scheme = scheme.lower()"]
    SchemeNorm --> HostNorm["parsed_host = encode_host(host)"]
    HostNorm --> PortNorm["parsed_port = normalize_port(port, scheme)"]
    PortNorm --> PathCheck{"has_scheme or has_authority?"}
    PathCheck -- "Yes" --> PathNorm["path = normalize_path(path)"]
    PathCheck -- "No" --> SkipPathNorm["Keep original path"]
    PathNorm --> QuoteComponents["Quote components with\nPATH_SAFE, QUERY_SAFE, FRAG_SAFE"]
    SkipPathNorm --> QuoteComponents
    
    subgraph "normalize_port() Logic"
        PortInput["Port Input"] --> DefaultCheck{"Port == default for scheme?"}
        DefaultCheck -- "Yes" --> ReturnNone["Return None"]
        DefaultCheck -- "No" --> ReturnPort["Return port as int"]
        DefaultPorts["Default Ports:\nhttp: 80, https: 443\nws: 80, wss: 443, ftp: 21"]
    end
```

| Normalization Type | Function/Logic | Result |
|-------------------|----------------|---------|
| **Scheme** | `scheme.lower()` | `HTTP` → `http` |
| **Host** | `encode_host()` → lowercase + IDNA encoding | Unicode domains → ASCII |
| **Port** | `normalize_port()` → remove defaults | `https://example.com:443` → port becomes `None` |
| **Path** | `normalize_path()` → resolve `./` and `../` | `/a/b/../c` → `/a/c` |
| **Components** | `quote()` with component-specific safe chars | Percent-encode unsafe characters |

Sources: [httpx/_urlparse.py:318-333](), [httpx/_urlparse.py:395-419](), [httpx/_urlparse.py:447-475](), [tests/models/test_url.py:246-278]()

## Special URL Handling

### IDNA Support

HTTPX supports Internationalized Domain Names through the `idna` package. Unicode domain names are automatically encoded to their ASCII representation (punycode) when normalized. [httpx/_urlparse.py:389-392]()

The `URL.host` property returns the Unicode version for readability, while `URL.raw_host` returns the IDNA-encoded bytes. [httpx/_urls.py:169-204]()

Sources: [httpx/_urlparse.py:11](), [httpx/_urls.py:42-55]()

### IPv4 and IPv6 Address Handling

HTTPX properly validates and formats IPv4 and IPv6 addresses in URLs:

- IPv4 addresses are validated using Python's `ipaddress` module. [httpx/_urlparse.py:352-358]()
- IPv6 addresses are enclosed in square brackets in the URL string, but accessed without brackets through the `host` property. [httpx/_urlparse.py:172](), [httpx/_urlparse.py:361-377]()

Sources: [httpx/_urlparse.py:154-155](), [tests/models/test_url.py:808-864]()

## URL Operations

### Creating URLs

URLs can be created from a string or from individual components via keyword arguments in the `URL` constructor. [httpx/_urls.py:77-114]()

Sources: [tests/models/test_url.py:383-394]()

### Modifying URLs

The `copy_with()` method allows creating a new URL with modified components by updating the internal `ParseResult`. [httpx/_urlparse.py:186-199]()

```mermaid
flowchart TD
    Original["Original URL Object"] --> CopyWith["copy_with()\nCreate new URL with\nmodified components"]
    CopyWith --> ValidateComponents["Validate Components"]
    ValidateComponents --> NewURL["New URL Object"]
    
    subgraph "Modifiable Components"
        Components["Components:
        - scheme
        - username
        - password
        - host
        - port
        - path
        - query
        - fragment
        - raw_path"]
    end
```

Sources: [httpx/_urls.py:119](), [tests/models/test_url.py:567-673]()

### URL Joining

The `join()` method follows RFC 3986 URL reference resolution, allowing relative URLs to be resolved against a base URL.

Sources: [tests/models/test_url.py:479-563]()

### Query Parameter Manipulation

HTTPX provides several methods for manipulating query parameters that return a new `URL` instance:

- `copy_set_param(key, value)`: Sets a query parameter.
- `copy_add_param(key, value)`: Adds a query parameter (allowing multiple values).
- `copy_remove_param(key)`: Removes a query parameter.
- `copy_merge_params(params)`: Merges a dictionary of parameters into the URL.

Sources: [tests/models/test_url.py:684-714]()

## Percent Encoding

Percent encoding is used to represent characters in URL components that would otherwise be unsafe or have special meaning. HTTPX implements percent encoding according to the WHATWG URL specification, with different safe character sets for different URL components. [httpx/_urlparse.py:39-45]()

### Encoding Logic

```mermaid
flowchart TD
    StringInput["Input String"] --> QuoteFunc["quote(string, safe)"]
    QuoteFunc --> FindPercent["Find existing %XX sequences\nwith PERCENT_ENCODED_REGEX"]
    FindPercent --> ProcessParts["Process text between\nencoded sequences"]
    ProcessParts --> PercentEncoded["percent_encoded(text, safe)"]
    PercentEncoded --> CheckSafe{"Character in\nUNRESERVED_CHARACTERS + safe?"}
    CheckSafe -- "Yes" --> KeepChar["Keep character"]
    CheckSafe -- "No" --> EncodeChar["PERCENT(char)\n→ %XX format"]
    
    subgraph "Safe Character Constants"
        PathSafe["PATH_SAFE\nExcludes: space \" # < > ? ` { }"]
        QuerySafe["QUERY_SAFE\nExcludes: space \" # < >"]
        FragSafe["FRAG_SAFE\nExcludes: space \" < > `"]
        UsernameSafe["USERNAME_SAFE\nMost restricted"]
        PasswordSafe["PASSWORD_SAFE\nMost restricted"]
    end
```

### Safe Character Sets by Component

| Component | Constant | Excluded Characters | Usage |
|-----------|----------|-------------------|--------|
| **Path** | `PATH_SAFE` | space `"` `#` `<` `>` `?` `` ` `` `{` `}` | `quote(path, safe=PATH_SAFE)` |
| **Query** | `QUERY_SAFE` | space `"` `#` `<` `>` | `quote(query, safe=QUERY_SAFE)` |
| **Fragment** | `FRAG_SAFE` | space `"` `<` `>` `` ` `` | `quote(frag, safe=FRAG_SAFE)` |
| **Username** | `USERNAME_SAFE` | Many characters including `/` `:` `;` `=` `@` | Used in userinfo encoding |
| **Password** | `PASSWORD_SAFE` | Many characters including `/` `:` `;` `=` `@` | Used in userinfo encoding |

Sources: [httpx/_urlparse.py:43-98](), [httpx/_urlparse.py:478-527](), [httpx/_urlparse.py:331-333]()

### Encoding Behavior

HTTPX's URL handling distinguishes between programmatic parameter addition (via `params=`) and URL string parsing:

```mermaid
flowchart TD
    URLConstruction{"URL Construction Method"}
    URLConstruction -- "params= argument" --> ParamsPath["QueryParams(params)\n→ urlencode() with +"]
    URLConstruction -- "URL string with query" --> StringPath["Parse existing query\nwith quote()"]
    
    ParamsPath --> FormEncoding["Form Encoding:\nSpaces → +\nSpecial chars → %XX"]
    StringPath --> URLEncoding["URL Encoding:\nSpaces → %20\nPreserve existing %XX"]
    
    subgraph "Implementation Details"
        ParamsImpl["URL.__init__() converts\nparams to QueryParams\nthen str(QueryParams)"]
        StringImpl["urlparse() uses\nquote(query, safe=QUERY_SAFE)"]
    end
```

Sources: [httpx/_urls.py:107-114](), [tests/models/test_url.py:286-337](), [tests/models/test_url.py:143-151]()

---

# Page: Headers and Cookies

# Headers and Cookies

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_models.py](httpx/_models.py)
- [tests/client/test_cookies.py](tests/client/test_cookies.py)
- [tests/client/test_headers.py](tests/client/test_headers.py)
- [tests/client/test_properties.py](tests/client/test_properties.py)
- [tests/client/test_queryparams.py](tests/client/test_queryparams.py)
- [tests/models/test_cookies.py](tests/models/test_cookies.py)

</details>



This page covers httpx's core data structures for handling HTTP headers and cookies, including the `Headers` and `Cookies` classes, their implementation details, and their integration with client instances.

## Headers System Overview

The httpx headers system provides case-insensitive access to HTTP headers with support for multiple values per header name. Headers flow through the request/response pipeline and are managed as a specialized mapping.

### Natural Language to Code Entity Mapping: Headers

```mermaid
graph TD
    subgraph "Natural Language Concepts"
        CaseInsensitivity["Case-insensitive Access"]
        MultiValue["Multi-value Support"]
        RawBytes["Raw Byte Representation"]
        SensitiveData["Sensitive Data Obfuscation"]
    end
    
    subgraph "Code Entities (httpx._models.py)"
        HeadersClass["class Headers"]
        NormalizeKey["_normalize_header_key()"]
        NormalizeValue["_normalize_header_value()"]
        Obfuscate["_obfuscate_sensitive_headers()"]
        SensitiveSet["SENSITIVE_HEADERS"]
    end
    
    CaseInsensitivity --- HeadersClass
    CaseInsensitivity --- NormalizeKey
    MultiValue --- HeadersClass
    RawBytes --- HeadersClass
    SensitiveData --- Obfuscate
    SensitiveData --- SensitiveSet
```

Sources: [httpx/_models.py:53-53](), [httpx/_models.py:67-83](), [httpx/_models.py:130-142]()

## Headers Class

The `httpx.Headers` class [httpx/_models.py:139-142]() implements `typing.MutableMapping[str, str]`. Internally, it maintains a list of three-tuples: `(raw_key, lower_key, value)` [httpx/_models.py:149-162]().

### Implementation Details

| Component | Logic | Source |
|-----------|-------|--------|
| **Normalization** | Keys and values are coerced to bytes (defaulting to ASCII) during initialization. | [httpx/_models.py:155-162]() |
| **Case-Insensitivity** | Lookups use the `lower_key` stored in the internal `_list`. | [httpx/_models.py:157-157]() |
| **Encoding** | Defaults to `ascii` or `utf-8`, falling back to `iso-8859-1` if decoding fails. | [httpx/_models.py:172-189]() |
| **Multi-value Access** | `__getitem__` returns a single string with values joined by `, `. | [httpx/_models.py:218-228]() |

### Key Methods

- `get_list(key, split_commas=False)`: Returns a list of all values for a specific header [httpx/_models.py:238-251]().
- `multi_items()`: Returns a list of all `(key, value)` pairs, including duplicates [httpx/_models.py:230-236]().
- `raw`: Property returning a list of `(bytes, bytes)` for the transport layer [httpx/_models.py:195-200]().

Sources: [httpx/_models.py:139-251]()

## Cookies System Overview

The `httpx.Cookies` class [httpx/_models.py:284-287]() wraps a standard library `http.cookiejar.CookieJar` [httpx/_models.py:291](). It provides a dictionary-like interface while supporting domain and path-specific cookie management.

### Natural Language to Code Entity Mapping: Cookies

```mermaid
graph TD
    subgraph "Natural Language Concepts"
        CookieStorage["Cookie Storage"]
        DomainPath["Domain & Path Awareness"]
        Persistence["Client Persistence"]
        ConflictHandling["Conflict Resolution"]
    end
    
    subgraph "Code Entities (httpx/_models.py)"
        CookiesClass["class Cookies"]
        InternalJar["self.jar (CookieJar)"]
        SetMethod["Cookies.set()"]
        GetMethod["Cookies.get()"]
        ConflictErr["CookieConflict exception"]
    end
    
    CookieStorage --- CookiesClass
    CookieStorage --- InternalJar
    DomainPath --- SetMethod
    DomainPath --- GetMethod
    Persistence --- CookiesClass
    ConflictHandling --- ConflictErr
```

Sources: [httpx/_models.py:284-300](), [httpx/_models.py:25-25]()

## Cookies Class

### Basic Usage and Conflict Resolution

`httpx.Cookies` allows simple access via `cookies["name"]`. However, if multiple cookies exist with the same name across different domains/paths, it raises a `httpx.CookieConflict` [httpx/_models.py:328-335]().

| Method | Description | Source |
|--------|-------------|--------|
| `set(name, value, [domain], [path])` | Sets a cookie with specific metadata. | [httpx/_models.py:350-384]() |
| `get(name, [default], [domain], [path])` | Retrieves a specific cookie value. | [httpx/_models.py:307-326]() |
| `delete(name, [domain], [path])` | Removes a specific cookie. | [httpx/_models.py:397-408]() |
| `extract_cookies(response)` | Populates the jar from `Set-Cookie` headers. | [httpx/_models.py:428-433]() |

### Integration with Client

Client instances persist cookies across the request/response lifecycle.

```mermaid
graph LR
    subgraph "Request Flow"
        Client["httpx.Client"]
        Req["httpx.Request"]
        Cookies["httpx.Cookies"]
    end
    
    subgraph "Response Flow"
        Resp["httpx.Response"]
        Jar["CookieJar"]
    end
    
    Client -- "1. set_cookie_header()" --> Req
    Req -- "2. HTTP Send" --> Resp
    Resp -- "3. extract_cookies()" --> Cookies
    Cookies -- "4. update jar" --> Jar
    Jar -- "5. Next Request" --> Client
```

Sources: [httpx/_models.py:420-426](), [httpx/_models.py:428-433](), [tests/client/test_cookies.py:151-169]()

## Advanced Header Features

### Sensitive Header Protection
The function `_obfuscate_sensitive_headers` [httpx/_models.py:130-137]() identifies keys in `SENSITIVE_HEADERS` (authorization, proxy-authorization) [httpx/_models.py:53-53]() and replaces their values with `[secure]` for logging and string representations.

### Link Header Parsing
The utility `_parse_header_links` [httpx/_models.py:93-127]() parses the `Link` entity-header field into a list of dictionaries, extracting URLs and associated parameters (e.g., `rel`, `type`).

### Host Header Logic
In requests, the `Host` header is automatically generated from the URL. It excludes user information and default ports (80 for HTTP, 443 for HTTPS) [tests/client/test_headers.py:188-210]().

Sources: [httpx/_models.py:53-137](), [tests/client/test_headers.py:188-210]()

---

# Page: Query Parameters

# Query Parameters

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_urlparse.py](httpx/_urlparse.py)
- [httpx/_urls.py](httpx/_urls.py)
- [tests/models/test_headers.py](tests/models/test_headers.py)
- [tests/models/test_queryparams.py](tests/models/test_queryparams.py)
- [tests/models/test_url.py](tests/models/test_url.py)

</details>



This document details how query parameters are handled in the `httpx` library. It focuses on the `httpx.QueryParams` class, an immutable multi-dict designed for URL query strings.

## Overview

The `httpx.QueryParams` class provides a dictionary-like interface for managing URL query parameters while supporting the multi-value nature of the HTTP query component. It is used internally by `httpx.URL` and `httpx.Request` to handle the `params` argument and the query portion of URLs.

```mermaid
graph TD
    subgraph "Data Model Space"
        QueryParams["httpx.QueryParams"]
        URL["httpx.URL"]
        Request["httpx.Request"]
    end

    subgraph "Logic Space"
        urlparse["httpx._urlparse.urlparse"]
        primitive_str["httpx._utils.primitive_value_to_str"]
    end

    URL -- "uses" --> QueryParams
    Request -- "uses" --> QueryParams
    URL -- "delegates parsing to" --> urlparse
    QueryParams -- "normalizes values with" --> primitive_str
```
Sources: [httpx/_urls.py:12-15](), [httpx/_urls.py:154-163](), [httpx/_urls.py:10-10]()

## The QueryParams Class

### Initialization and Types
`QueryParams` can be instantiated from several formats defined by `QueryParamTypes` [httpx/_urls.py:8-8](). Supported inputs include:
*   **Strings**: Raw query strings like `"a=1&b=2"` [tests/models/test_queryparams.py:9-9]().
*   **Mappings**: Dictionaries where values can be primitives or sequences (e.g., `{"a": ["1", "2"]}`) [tests/models/test_queryparams.py:10-11]().
*   **Sequences of Pairs**: Lists or tuples of `(key, value)` tuples [tests/models/test_queryparams.py:12-13]().

### Immutability Pattern
Unlike a standard Python `dict`, `httpx.QueryParams` is immutable. Direct assignment or the `update()` method will raise a `RuntimeError` [tests/models/test_queryparams.py:90-100](). Any operation that modifies the parameters returns a **new instance**.

| Method | Description | Source |
| :--- | :--- | :--- |
| `set(key, value)` | Returns a new instance with the key set to the provided value, removing existing entries for that key. | [tests/models/test_queryparams.py:102-106]() |
| `add(key, value)` | Returns a new instance with an additional entry for the key, preserving existing values. | [tests/models/test_queryparams.py:108-112]() |
| `remove(key)` | Returns a new instance with all entries for the specified key removed. | [tests/models/test_queryparams.py:114-118]() |
| `merge(params)` | Returns a new instance where the provided parameters overwrite or extend the existing ones. | [tests/models/test_queryparams.py:120-126]() |

### Value Normalization
HTTPX converts Python primitives into string representations suitable for URLs:
*   `True` / `False` become `"true"` / `"false"` [tests/models/test_queryparams.py:57-62]().
*   `None` or `""` result in an empty value (e.g., `a=`) [tests/models/test_queryparams.py:63-67]().
*   `int` and `float` are cast to their string forms [tests/models/test_queryparams.py:69-73]().

## Integration with URL and Request

The `httpx.URL` class manages its query component via `QueryParams`. When a `URL` is initialized with the `params` keyword, it replaces the existing query string with the serialized version of those parameters [httpx/_urls.py:107-114]().

```mermaid
sequenceDiagram
    participant User
    participant URL as httpx.URL
    participant QP as httpx.QueryParams
    participant Parser as httpx._urlparse.urlparse

    User->>URL: URL("http://host/path", params={"a": 1})
    URL->>QP: QueryParams({"a": 1})
    QP-->>URL: "a=1"
    URL->>Parser: urlparse(url, query="a=1")
    Parser-->>URL: ParseResult
    URL-->>User: URL instance
```
Sources: [httpx/_urls.py:77-125](), [httpx/_urlparse.py:213-213]()

### URL Encoding Behavior
HTTPX differentiates between a query string provided in the URL and parameters provided via the `params` argument:
*   **URL String**: If the URL is initialized as `httpx.URL("https://example.com/?a=b c")`, spaces may be preserved as `%20` or `+` depending on the input [tests/models/test_url.py:144-148]().
*   **Params Argument**: Using `params={"a": "b c"}` ensures standard encoding, typically resulting in `a=b+c` [tests/models/test_url.py:150-151]().

## Accessing Data
Because a query string can contain multiple values for one key, `QueryParams` provides two ways to access data:
1.  **Standard Access**: `q["key"]` or `q.get("key")` returns the **first** value associated with that key [tests/models/test_queryparams.py:21-22]().
2.  **Multi-value Access**: `q.get_list("key")` returns a **list of all values** for that key [tests/models/test_queryparams.py:24-24]().

### Serialization
Calling `str(query_params)` produces a URL-encoded string. If a key was provided without a value or with `None`, the output includes the trailing `=` (e.g., `a=`) [tests/models/test_queryparams.py:80-88]().

Sources: [tests/models/test_queryparams.py:1-137](), [httpx/_urls.py:1-125]()

---

# Page: Content Encoding and Decoding

# Content Encoding and Decoding

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_content.py](httpx/_content.py)
- [httpx/_decoders.py](httpx/_decoders.py)
- [tests/test_content.py](tests/test_content.py)
- [tests/test_decoders.py](tests/test_decoders.py)

</details>



This document covers how httpx handles content encoding and decoding for HTTP requests and responses. This includes compression algorithms (gzip, deflate, brotli, zstd), character encoding detection and conversion, and the transformation of various Python data types into HTTP message bodies.

For information about multipart form data specifically, see [4.7 Multipart Form Data](). For details about request and response objects themselves, see [4.1 Request Objects]() and [4.2 Response Objects]().

## Content Processing Pipeline

httpx processes content through a multi-stage pipeline that handles both compression/decompression and character encoding. The system is designed to work transparently with both synchronous and asynchronous streams.

```mermaid
graph TD
    subgraph "Request Encoding Pipeline"
        PythonData["Python Data<br/>(dict, str, bytes, etc.)"]
        ContentEncoder["Content Encoders<br/>encode_json, encode_urlencoded_data"]
        RequestStream["Request Stream<br/>ByteStream, IteratorByteStream"]
        HTTPMessage["HTTP Request Message"]
        
        PythonData --> ContentEncoder
        ContentEncoder --> RequestStream
        RequestStream --> HTTPMessage
    end
    
    subgraph "Response Decoding Pipeline"
        HTTPResponse["HTTP Response Message"]
        CompressionDecoder["Compression Decoders<br/>GZipDecoder, BrotliDecoder"]
        RawBytes["Raw Bytes"]
        TextDecoder["Character Decoder<br/>TextDecoder"]
        PythonContent["Python Content<br/>.text, .json(), .content"]
        
        HTTPResponse --> CompressionDecoder
        CompressionDecoder --> RawBytes
        RawBytes --> TextDecoder
        TextDecoder --> PythonContent
    end
    
    subgraph "Stream Processing"
        ChunkProcessing["Chunking<br/>ByteChunker, TextChunker"]
        LineProcessing["Line Processing<br/>LineDecoder"]
        
        RawBytes --> ChunkProcessing
        PythonContent --> LineProcessing
    end
```

Sources: [httpx/_decoders.py:36-394](), [httpx/_content.py:1-241]()

## Response Content Compression Decoding

httpx automatically detects and decodes compressed response content based on the `Content-Encoding` header. The system supports multiple compression algorithms and can handle chained encodings.

### Supported Compression Algorithms

| Algorithm | Header Value | Decoder Class | Requirements |
|-----------|-------------|---------------|--------------|
| Identity | `identity` | `IdentityDecoder` | Built-in |
| Deflate | `deflate` | `DeflateDecoder` | Built-in |
| Gzip | `gzip` | `GZipDecoder` | Built-in |
| Brotli | `br` | `BrotliDecoder` | `pip install httpx[brotli]` |
| Zstandard | `zstd` | `ZStandardDecoder` | `pip install httpx[zstd]` |

```mermaid
graph TD
    ContentEncodingHeader["Content-Encoding Header"]
    DecoderFactory["SUPPORTED_DECODERS mapping"]
    SingleDecoder["Single Decoder Instance"]
    MultiDecoder["MultiDecoder Instance"]
    CompressedBytes["Compressed Bytes"]
    DecodedBytes["Decoded Bytes"]
    
    ContentEncodingHeader --> DecoderFactory
    DecoderFactory --> SingleDecoder
    DecoderFactory --> MultiDecoder
    
    CompressedBytes --> SingleDecoder
    CompressedBytes --> MultiDecoder
    SingleDecoder --> DecodedBytes
    MultiDecoder --> DecodedBytes
    
    subgraph "Decoder Implementations"
        IdentityDecoder["IdentityDecoder<br/>httpx._decoders.IdentityDecoder"]
        GZipDecoder["GZipDecoder<br/>httpx._decoders.GZipDecoder"]
        DeflateDecoder["DeflateDecoder<br/>httpx._decoders.DeflateDecoder"]
        BrotliDecoder["BrotliDecoder<br/>httpx._decoders.BrotliDecoder"]
        ZStandardDecoder["ZStandardDecoder<br/>httpx._decoders.ZStandardDecoder"]
    end
```

Sources: [httpx/_decoders.py:36-106](), [httpx/_decoders.py:108-159](), [httpx/_decoders.py:161-201](), [httpx/_decoders.py:381-394]()

### Compression Decoder Implementation

Each decoder follows the `ContentDecoder` interface with `decode()` and `flush()` methods:

- **IdentityDecoder**: Passes data through unchanged for uncompressed content [httpx/_decoders.py:44-54]().
- **DeflateDecoder**: Handles deflate compression with automatic fallback between zlib and raw deflate formats using `zlib.decompressobj()` [httpx/_decoders.py:56-83]().
- **GZipDecoder**: Uses zlib with `zlib.MAX_WBITS | 16` for gzip format detection [httpx/_decoders.py:85-106]().
- **BrotliDecoder**: Supports both `brotli` and `brotlicffi` packages [httpx/_decoders.py:108-159]().
- **ZStandardDecoder**: Handles zstd compression with multi-frame support by checking `self.decompressor.unused_data` [httpx/_decoders.py:161-201]().

The `MultiDecoder` class handles responses with multiple content encodings applied (e.g., `"deflate, gzip"`), processing them in reverse order of the list passed to its constructor [httpx/_decoders.py:203-226]().

Sources: [httpx/_decoders.py:36-42](), [httpx/_decoders.py:56-83](), [httpx/_decoders.py:203-226](), [httpx/_decoders.py:186-189]()

## Response Character Encoding

httpx handles character encoding detection and conversion to transform raw bytes into text content.

```mermaid
graph TD
    RawBytes["Raw Response Bytes"]
    ContentTypeHeader["Content-Type Header<br/>charset parameter"]
    AutoDetect["Auto-detection<br/>chardet library"]
    UTF8Fallback["UTF-8 Fallback"]
    TextContent["Decoded Text Content"]
    
    RawBytes --> ContentTypeHeader
    ContentTypeHeader --> TextContent
    
    RawBytes --> AutoDetect
    AutoDetect --> TextContent
    
    RawBytes --> UTF8Fallback
    UTF8Fallback --> TextContent
    
    subgraph "Encoding Priority"
        Priority1["1. Content-Type charset"]
        Priority2["2. default_encoding callable"]
        Priority3["3. UTF-8 fallback"]
    end
    
    subgraph "TextDecoder Implementation"
        IncrementalDecoder["codecs.getincrementaldecoder"]
        ErrorHandling["errors='replace'"]
        StreamingSupport["Streaming decode/flush"]
    end
```

Sources: [httpx/_decoders.py:306-319](), [tests/test_decoders.py:234-245]()

### Character Encoding Detection

The encoding detection process follows this hierarchy:

1. **Content-Type Header**: Extract charset from `Content-Type: text/html; charset=utf-8`.
2. **Custom Autodetect**: Use a `default_encoding` callable if provided.
3. **UTF-8 Fallback**: Default assumption for text content.

The `TextDecoder` class uses Python's `codecs.getincrementaldecoder` to handle character conversion, ensuring multi-byte characters are handled correctly across chunk boundaries [httpx/_decoders.py:306-319]().

Sources: [httpx/_decoders.py:306-319](), [tests/test_decoders.py:234-245]()

## Request Content Encoding

httpx provides several encoding functions in `httpx._content` to transform Python data structures into HTTP request bodies.

### Content Encoding Functions

```mermaid
graph LR
    subgraph "Python Data Types"
        StringData["str"]
        BytesData["bytes"] 
        JSONData["dict/list"]
        FormData["dict (form)"]
        FileData["file-like objects"]
        StreamData["Iterable[bytes]"]
    end
    
    subgraph "Encoding Functions"
        EncodeContent["httpx._content.encode_content"]
        EncodeJSON["httpx._content.encode_json"]
        EncodeURLEncoded["httpx._content.encode_urlencoded_data"]
        EncodeMultipart["httpx._content.encode_multipart_data"]
        EncodeText["httpx._content.encode_text"]
    end
    
    subgraph "Output"
        Headers["Headers dict"]
        Stream["ByteStream/IteratorByteStream"]
    end
    
    StringData --> EncodeContent
    BytesData --> EncodeContent
    JSONData --> EncodeJSON
    FormData --> EncodeURLEncoded
    FileData --> EncodeMultipart
    StreamData --> EncodeContent
    
    EncodeContent --> Headers
    EncodeContent --> Stream
    EncodeJSON --> Headers
    EncodeJSON --> Stream
    EncodeURLEncoded --> Headers
    EncodeURLEncoded --> Stream
```

Sources: [httpx/_content.py:107-134](), [httpx/_content.py:136-184](), [httpx/_content.py:186-219]()

### Encoding Function Details

| Function | Input Type | Content-Type | Length Strategy |
|----------|------------|-------------|-----------------|
| `encode_content()` | `str`, `bytes`, `Iterable`, `AsyncIterable` | None set | Length for bytes/str, chunked for iterables [httpx/_content.py:107-134]() |
| `encode_json()` | Any JSON-serializable | `application/json` | Content-Length [httpx/_content.py:176-184]() |
| `encode_urlencoded_data()` | `Mapping` | `application/x-www-form-urlencoded` | Content-Length [httpx/_content.py:136-149]() |
| `encode_text()` | `str` | `text/plain; charset=utf-8` | Content-Length [httpx/_content.py:160-166]() |
| `encode_html()` | `str` | `text/html; charset=utf-8` | Content-Length [httpx/_content.py:168-174]() |

The `encode_request()` function serves as the main dispatcher, selecting the appropriate encoding based on parameters like `json`, `data`, `files`, or `content` [httpx/_content.py:186-219]().

Sources: [httpx/_content.py:107-219]()

## Stream Processing and Chunking

httpx supports streaming content through specialized classes that work with both synchronous and asynchronous streams.

### Stream Types
- **ByteStream**: Wraps static `bytes` content [httpx/_content.py:31-40]().
- **IteratorByteStream**: Wraps synchronous iterables. It handles file-like objects using `.read(CHUNK_SIZE)` [httpx/_content.py:42-65]().
- **AsyncIteratorByteStream**: Wraps asynchronous iterables. It handles async file-like objects using `.aread(CHUNK_SIZE)` [httpx/_content.py:67-89]().

### Chunking and Line Decoding
- **ByteChunker**: Accumulates bytes and yields fixed-size chunks [httpx/_decoders.py:228-265]().
- **TextChunker**: Accumulates text and yields fixed-size chunks [httpx/_decoders.py:267-304]().
- **LineDecoder**: Detects line endings (`\n`, `\r`, `\r\n`) across chunk boundaries [httpx/_decoders.py:321-379]().

Sources: [httpx/_content.py:31-89](), [httpx/_decoders.py:228-379]()

## Error Handling

httpx uses `DecodingError` to signal failures in the decoding pipeline.

- **Compression Failures**: If `zlib` or `brotli` encounter malformed data, a `DecodingError` is raised [httpx/_decoders.py:76, 99, 143, 191]().
- **Truncated Data**: `ZStandardDecoder` raises `DecodingError` if the stream is incomplete upon calling `.flush()` [httpx/_decoders.py:199]().
- **Stream State**: Attempting to iterate over a consumed generator stream results in `httpx.StreamConsumed` [httpx/_content.py:52, 77](). Accessing a pickled stream results in `httpx.StreamClosed` [httpx/_content.py:92-105]().

Sources: [httpx/_decoders.py:14, 76, 99, 143, 191, 199](), [httpx/_content.py:16, 52, 77, 92-105](), [tests/test_decoders.py:91-120]()

---

# Page: Multipart Form Data

# Multipart Form Data

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_multipart.py](httpx/_multipart.py)
- [tests/test_multipart.py](tests/test_multipart.py)

</details>



This document covers httpx's multipart form data implementation, which enables the creation of `multipart/form-data` encoded HTTP requests for file uploads and mixed form content. This functionality is primarily used when submitting forms that contain both regular text fields and file attachments.

For information about general content encoding and decoding, see [Content Encoding and Decoding](#4.6). For details about request objects and their construction, see [Request Objects](#4.1).

## Overview

The multipart form data system in httpx handles the creation of RFC 2046 compliant multipart content streams. When a request includes both `data` and `files` parameters, or when the `files` parameter is provided alone, httpx automatically creates a multipart encoded request body with appropriate boundaries and headers.

The system supports various file input formats including file-like objects, raw bytes, strings, and tuples containing filename and content type information. It automatically handles content type detection, boundary generation, and proper field encoding.

### Data Flow and Code Entity Association

The following diagram bridges the natural language concepts of form submission to the specific classes and functions in `httpx/_multipart.py`.

```mermaid
graph TB
    subgraph "Request Construction Space"
        UserCode["User Code"] -- "calls" --> RequestBuilder["httpx.Request()"]
        DataParam["data={'field': 'value'}"] -.-> RequestBuilder
        FilesParam["files={'upload': file_obj}"] -.-> RequestBuilder
    end
    
    subgraph "Code Entity Space: httpx/_multipart.py"
        RequestBuilder -- "instantiates" --> MultipartStream["class MultipartStream"]
        MultipartStream -- "creates" --> DataField["class DataField"]
        MultipartStream -- "creates" --> FileField["class FileField"] 
        
        DataField -- "uses" --> FormatParam["_format_form_param()"]
        FileField -- "uses" --> GuessType["_guess_content_type()"]
    end
    
    subgraph "Output Space"
        MultipartStream -- "yields" --> ContentStream["bytes chunks"]
        ContentStream --> HTTPRequest["Final HTTP Request"]
        MultipartStream -- "provides" --> ContentTypeHeader["Content-Type: multipart/form-data"]
    end
```

**Sources:** [httpx/_multipart.py:224-301](), [tests/test_multipart.py:17-42]()

## Core Components

The multipart system consists of three main classes that work together to create properly formatted multipart content:

### MultipartStream Class

The `MultipartStream` class serves as the primary interface for creating multipart encoded content. It implements both `SyncByteStream` and `AsyncByteStream` interfaces, allowing it to be used in both synchronous and asynchronous contexts. It manages the lifecycle of the boundary and the collection of fields.

```mermaid
graph LR
    subgraph "MultipartStream Lifecycle"
        Constructor["__init__"] --> BoundaryCreation["Generate Random Boundary"]
        Constructor --> DataProcessing["Process RequestData"]
        Constructor --> FilesProcessing["Process RequestFiles"]
        
        DataProcessing --> DataFields["DataField(name, value)"]
        FilesProcessing --> FileFields["FileField(name, value)"]
        
        BoundaryCreation --> HeaderGen["Set headers['Content-Type']"]
    end
    
    subgraph "Streaming Implementation"
        IterChunks["iter_chunks() / __iter__()"] --> BoundaryPrefix["b'--' + boundary + b'\\r\\n'"]
        IterChunks --> FieldContent["Field.render()"]
        IterChunks --> FieldSuffix["b'\\r\\n'"]
        IterChunks --> FinalBoundary["b'--' + boundary + b'--\\r\\n'"]
    end
```

**Sources:** [httpx/_multipart.py:224-301](), [httpx/_multipart.py:303-316]()

### DataField Class

The `DataField` class represents individual form fields containing text or primitive data values. It handles proper encoding of field names and values according to HTML5 form encoding standards. It validates that names are strings and values are primitive types.

| Method | Purpose | Returns |
|--------|---------|---------|
| `render_headers()` | Generates `Content-Disposition: form-data; name="..."` | `bytes` |
| `render_data()` | Encodes field value as bytes using `to_bytes()` | `bytes` |
| `get_length()` | Calculates total field size (headers + data) | `int` |
| `render()` | Yields headers and data sequentially | `Iterator[bytes]` |

**Sources:** [httpx/_multipart.py:70-113]()

### FileField Class

The `FileField` class handles file uploads and supports various input formats. It manages the complexity of the 4-element tuple API (filename, fileobj, content_type, headers) and performs automatic MIME type guessing.

```mermaid
graph TB
    subgraph "Input Handling in FileField.__init__"
        Tuple4["(filename, fileobj, type, headers)"] --> Init["FileField"]
        Tuple2["(filename, fileobj)"] --> Init
        RawFile["File-like object"] --> Init
        
        Init --> Guess["_guess_content_type()"]
        Init --> CheckBinary["Check for binary mode"]
    end
    
    subgraph "Rendering Logic"
        Init --> RenderHeaders["render_headers()"]
        Init --> RenderData["render_data()"]
        
        RenderData -- "if seekable" --> Seek0["file.seek(0)"]
        RenderData -- "loop" --> ChunkRead["read(CHUNK_SIZE)"]
    end
    
    ChunkRead --> FinalBytes["Yielded bytes"]
```

**Sources:** [httpx/_multipart.py:115-222](), [httpx/_multipart.py:45-53]()

## File Input Formats

The multipart system supports several file input formats to accommodate different use cases, mirroring the `requests` library API:

1.  **Simple File Object**: `files = {'upload': open('file.txt', 'rb')}`. The filename is extracted from the file object's `.name` attribute if available [httpx/_multipart.py:145-146]().
2.  **Tuple with Filename**: `files = {'upload': ('custom_name.txt', file_content)}` [httpx/_multipart.py:138]().
3.  **Tuple with Content Type**: `files = {'upload': ('file.txt', file_content, 'text/plain')}` [httpx/_multipart.py:140]().
4.  **Tuple with Custom Headers**: `files = {'upload': ('file.txt', file_content, 'text/plain', {'Expires': '0'})}` [httpx/_multipart.py:143]().

**Sources:** [httpx/_multipart.py:134-157](), [tests/test_multipart.py:124-150]()

## Boundary Management

The multipart system generates random boundaries using `os.urandom(16).hex()` to ensure uniqueness [httpx/_multipart.py:235-241](). 

If a `Content-Type` header is explicitly provided by the user, httpx attempts to extract the boundary using `get_multipart_boundary_from_content_type()`. This function parses the header according to RFC 2046, handling both quoted and unquoted boundary values [httpx/_multipart.py:56-67]().

**Sources:** [httpx/_multipart.py:56-67](), [httpx/_multipart.py:235-241](), [tests/test_multipart.py:44-77]()

## Content Length Handling

The `MultipartStream` calculates the total `Content-Length` by summing the lengths of all fields and boundaries. However, if any field (specifically a `FileField`) has an unknown length (e.g., a non-seekable stream), the total length becomes `None`.

| Scenario | Behavior |
|----------|----------|
| **Seekable File** | `peek_filelike_length()` is used to determine size without reading [httpx/_multipart.py:177-184](). |
| **Non-seekable/Unknown** | `get_length()` returns `None` [httpx/_multipart.py:182](). |
| **Overall Stream** | If `get_length()` is `None`, the request will typically use chunked transfer encoding [httpx/_multipart.py:287-292](). |

**Sources:** [httpx/_multipart.py:171-184](), [httpx/_multipart.py:287-292](), [tests/test_multipart.py:382-421]()

## HTML5 Form Encoding

The system implements proper HTML5 form parameter encoding for field names and filenames via the `_format_form_param()` function. This handles special characters and ensures compatibility with modern web standards:

-   **Replacements**: Double quotes (`"`) are encoded as `%22`, and backslashes (`\`) are escaped as `\\\\` [httpx/_multipart.py:24-30]().
-   **Control Characters**: Characters in the range `0x00-0x1F` (excluding `0x1B`) are percent-encoded [httpx/_multipart.py:26-27]().

**Sources:** [httpx/_multipart.py:24-42](), [tests/test_multipart.py:442-470]()

## Error Handling and Validation

Httpx performs strict validation during field initialization to prevent malformed requests:

-   **DataField Validation**: Raises `TypeError` if the field name is not a string or if the value is not a primitive type (str, bytes, int, float, None) [httpx/_multipart.py:76-84]().
-   **FileField Validation**: Raises `TypeError` if an `io.StringIO` or a text-mode file object is provided. Multipart uploads require binary mode [httpx/_multipart.py:158-165]().

**Sources:** [httpx/_multipart.py:76-84](), [httpx/_multipart.py:158-165](), [tests/test_multipart.py:367-380]()

---

# Page: Transport System

# Transport System

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_transports/base.py](httpx/_transports/base.py)
- [httpx/_transports/default.py](httpx/_transports/default.py)
- [httpx/_transports/mock.py](httpx/_transports/mock.py)

</details>



The transport system in httpx provides a pluggable abstraction layer that handles the actual transmission of HTTP requests and responses. It separates the high-level client logic (like cookie handling and redirect following) from low-level network operations, enabling different transport mechanisms including standard HTTP connections, direct ASGI/WSGI application integration, and mock implementations for testing.

For information about specific transport configurations, see [Transport Architecture](#5.1). For direct application integration, see [ASGI and WSGI Integration](#5.2). For proxy configuration details, see [Proxy Support](#5.3). For testing with mock transports, see [Mock Transports](#5.4).

## Transport Abstraction Layer

The transport system is built around two base abstract classes that define the core transport interface. These classes require implementations to handle the transition from a `Request` object to a `Response` object.

| Transport Base Class | Purpose | Key Method |
|---------------------|---------|------------|
| `BaseTransport` | Synchronous transport interface | `handle_request()` |
| `AsyncBaseTransport` | Asynchronous transport interface | `handle_async_request()` |

```mermaid
graph TD
    subgraph "Transport Abstraction"
        BaseTransport["BaseTransport"]
        AsyncBaseTransport["AsyncBaseTransport"]
    end
    
    subgraph "Concrete Implementations"
        HTTPTransport["HTTPTransport<br/>httpcore backend"]
        AsyncHTTPTransport["AsyncHTTPTransport<br/>httpcore backend"]
        WSGITransport["WSGITransport<br/>Direct WSGI calls"]
        ASGITransport["ASGITransport<br/>Direct ASGI calls"]
        MockTransport["MockTransport<br/>Testing handler"]
    end
    
    BaseTransport --> HTTPTransport
    BaseTransport --> WSGITransport
    BaseTransport --> MockTransport
    AsyncBaseTransport --> AsyncHTTPTransport
    AsyncBaseTransport --> ASGITransport
    AsyncBaseTransport --> MockTransport
```

**Transport Interface Components**

Sources: [httpx/_transports/base.py:14-63](), [httpx/_transports/base.py:65-87](), [httpx/_transports/default.py:58-58]()

## Built-in Transport Implementations

httpx provides several built-in transport implementations for different use cases:

```mermaid
graph LR
    subgraph "Network Transports"
        HTTPTransport["HTTPTransport"]
        AsyncHTTPTransport["AsyncHTTPTransport"]
        HTTPCorePool["httpcore.ConnectionPool"]
        AsyncHTTPCorePool["httpcore.AsyncConnectionPool"]
    end
    
    subgraph "Direct App Transports"
        WSGITransport["WSGITransport"]
        ASGITransport["ASGITransport"]
        WSGIApp["WSGI Application"]
        ASGIApp["ASGI Application"]
    end
    
    subgraph "Testing Transports"
        MockTransport["MockTransport"]
        MockHandler["handler(request) -> Response"]
    end
    
    HTTPTransport --> HTTPCorePool
    AsyncHTTPTransport --> AsyncHTTPCorePool
    WSGITransport --> WSGIApp
    ASGITransport --> ASGIApp  
    MockTransport --> MockHandler
```

### HTTP Transports

The default `HTTPTransport` and `AsyncHTTPTransport` classes provide full-featured HTTP client functionality backed by the `httpcore` library. These transports manage the lifecycle of network connections, including HTTP/1.1 and HTTP/2 protocol support, connection pooling, and SSL/TLS.

The transports initialize appropriate `httpcore` backends based on the provided configuration:

| Configuration | httpcore Class | Purpose |
|--------------|---------------|---------|
| No proxy | `httpcore.ConnectionPool` | Direct network connections |
| HTTP proxy | `httpcore.HTTPProxy` | HTTP/HTTPS proxy tunneling |
| SOCKS proxy | `httpcore.SOCKSProxy` | SOCKS5 proxy tunneling |

Sources: [httpx/_transports/default.py:135-216](), [httpx/_transports/default.py:279-359]()

### Response Stream Handling

The HTTP transports wrap `httpcore` response streams in `ResponseStream` (sync) or `AsyncResponseStream` (async) classes. This wrapping ensures that data chunks yielded by the backend are processed within an exception-mapping context.

```mermaid
graph TD
    subgraph "httpcore Layer"
        HTTPCoreStream["httpcore_stream"]
    end
    
    subgraph "httpx Transport Layer"
        ResponseStream["ResponseStream<br/>(SyncByteStream)"]
        AsyncResponseStream["AsyncResponseStream<br/>(AsyncByteStream)"]
        MapExc["map_httpcore_exceptions()"]
    end
    
    HTTPCoreStream --> ResponseStream
    HTTPCoreStream --> AsyncResponseStream
    ResponseStream --> MapExc
    AsyncResponseStream --> MapExc
```

Sources: [httpx/_transports/default.py:121-133](), [httpx/_transports/default.py:265-277]()

## Transport Selection and Mounting

httpx clients use a "mounts" system to route requests to specific transports based on the request URL. By default, a client mounts a standard `HTTPTransport` to handle all traffic, but users can override this for specific domains or protocols (e.g., routing `http://local-app/` to an `ASGITransport`).

Sources: [httpx/_transports/default.py:12-25]()

## Transport Configuration

Transports are configured during initialization through several key objects that control connection behavior and security:

### Core Configuration Classes

| Configuration Class | Purpose | Key Parameters |
|-------------------|---------|---------------|
| `Limits` | Connection pooling limits | `max_connections`, `max_keepalive_connections` |
| `Proxy` | Proxy server configuration | `url`, `auth`, `headers` |
| `ssl.SSLContext` | Security settings | `verify`, `cert` |

```mermaid
graph TD
    subgraph "Transport Initialization"
        Init["HTTPTransport.__init__"]
        
        subgraph "Input Config"
            Limits["httpx.Limits"]
            Proxy["httpx.Proxy"]
            SSL["create_ssl_context()"]
        end
        
        subgraph "Backend Engine"  
            Core["httpcore.ConnectionPool"]
        end
    end
    
    Init --> Limits
    Init --> Proxy
    Init --> SSL
    Limits --> Core
    Proxy --> Core
    SSL --> Core
```

Sources: [httpx/_transports/default.py:136-154](), [httpx/_transports/default.py:156-167]()

## Integration with httpcore

The HTTP transports serve as an adapter layer. They map httpx's internal `Request` and `Response` models to the formats expected by `httpcore`, and provide comprehensive exception mapping.

### Exception Mapping

The `map_httpcore_exceptions()` context manager translates low-level `httpcore` exceptions (like `httpcore.ReadTimeout`) into their high-level httpx equivalents (like `httpx.ReadTimeout`). This ensures that users only need to catch httpx-branded exceptions.

| httpcore Exception | httpx Exception |
|-------------------|-----------------|
| `httpcore.ConnectTimeout` | `httpx.ConnectTimeout` |
| `httpcore.NetworkError` | `httpx.NetworkError` |
| `httpcore.ProtocolError` | `httpx.ProtocolError` |

Sources: [httpx/_transports/default.py:74-92](), [httpx/_transports/default.py:95-119]()

---

# Page: Transport Architecture

# Transport Architecture

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [docs/advanced/clients.md](docs/advanced/clients.md)
- [docs/advanced/transports.md](docs/advanced/transports.md)
- [docs/third_party_packages.md](docs/third_party_packages.md)
- [docs/troubleshooting.md](docs/troubleshooting.md)
- [httpx/_transports/base.py](httpx/_transports/base.py)
- [httpx/_transports/default.py](httpx/_transports/default.py)
- [httpx/_transports/mock.py](httpx/_transports/mock.py)

</details>



This document explains httpx's pluggable transport architecture, which provides an abstraction layer between the high-level client API and the actual network communication mechanisms. The transport system enables httpx to support multiple backend implementations, proxy configurations, and custom request handling strategies while maintaining a consistent interface.

For information about specific transport implementations like ASGI and WSGI integration, see [ASGI and WSGI Integration](#5.2). For proxy configuration details, see [Proxy Support](#5.3). For testing with mock transports, see [Mock Transports](#5.4).

## Transport Abstraction Layer

The transport architecture is built around base classes that define the interface for handling HTTP requests. The system supports both synchronous and asynchronous operations through separate base classes.

```mermaid
graph TB
    subgraph "Base Classes"
        BaseTransport["BaseTransport<br/>handle_request()"]
        AsyncBaseTransport["AsyncBaseTransport<br/>handle_async_request()"]
    end
    
    subgraph "Core Implementations"
        HTTPTransport["HTTPTransport<br/>httpcore backend"]
        AsyncHTTPTransport["AsyncHTTPTransport<br/>httpcore async backend"]
    end
    
    subgraph "Specialized Transports"
        ASGITransport["ASGITransport<br/>direct app calls"]
        WSGITransport["WSGITransport<br/>direct app calls"]
        MockTransport["MockTransport<br/>handler functions"]
    end
    
    subgraph "Client Integration"
        Client["Client<br/>sync requests"]
        AsyncClient["AsyncClient<br/>async requests"]
    end
    
    BaseTransport --> HTTPTransport
    AsyncBaseTransport --> AsyncHTTPTransport
    BaseTransport --> ASGITransport
    BaseTransport --> WSGITransport
    BaseTransport --> MockTransport
    
    HTTPTransport --> Client
    AsyncHTTPTransport --> AsyncClient
    ASGITransport --> Client
    WSGITransport --> Client
    MockTransport --> Client
```

Transport classes must implement either `handle_request()` for synchronous operations or `handle_async_request()` for asynchronous operations. These methods accept a `Request` object and return a `Response` object.

**Sources:** [httpx/_transports/base.py:14-63](), [httpx/_transports/base.py:65-87](), [httpx/_transports/default.py:135-263](), [httpx/_transports/default.py:279-406]()

## HTTPTransport Implementation

The default `HTTPTransport` and `AsyncHTTPTransport` classes provide the primary HTTP communication functionality by wrapping the `httpcore` library. These transports handle HTTP/1.1, HTTP/2, connection pooling, and proxy support.

```mermaid
graph LR
    subgraph "Request Processing"
        Request["Request<br/>method, url, headers, stream"]
        HTTPCoreRequest["httpcore.Request<br/>converted format"]
        HTTPCoreResponse["httpcore.Response<br/>status, headers, stream"]
        Response["Response<br/>final httpx format"]
    end
    
    subgraph "HTTPTransport Components"
        HTTPTransport["HTTPTransport<br/>handle_request()"]
        ConnectionPool["httpcore.ConnectionPool<br/>or HTTPProxy/SOCKSProxy"]
        ResponseStream["ResponseStream<br/>SyncByteStream wrapper"]
    end
    
    Request --> HTTPTransport
    HTTPTransport --> HTTPCoreRequest
    HTTPCoreRequest --> ConnectionPool
    ConnectionPool --> HTTPCoreResponse
    HTTPCoreResponse --> ResponseStream
    ResponseStream --> Response
```

The transport initialization process creates the appropriate `httpcore` backend based on proxy configuration:

| Configuration | httpcore Backend | Use Case |
|---------------|------------------|----------|
| No proxy | `httpcore.ConnectionPool` | Direct HTTP connections |
| HTTP/HTTPS proxy | `httpcore.HTTPProxy` | Standard proxy routing |
| SOCKS proxy | `httpcore.SOCKSProxy` | SOCKS5 proxy routing |

Advanced configuration such as `local_address`, `uds` (Unix Domain Sockets), and `retries` are managed at this level.

**Sources:** [httpx/_transports/default.py:135-216](), [httpx/_transports/default.py:279-359](), [docs/advanced/transports.md:5-36]()

## Exception Handling and Mapping

The transport layer maps `httpcore` exceptions to `httpx` exceptions, providing a consistent error interface regardless of the underlying HTTP implementation. This mapping is established dynamically to avoid import dependencies if `httpcore` is not present.

```mermaid
graph TB
    subgraph "httpcore Exceptions"
        HTTPCoreTimeout["httpcore.TimeoutException"]
        HTTPCoreConnect["httpcore.ConnectError"] 
        HTTPCoreRead["httpcore.ReadError"]
        HTTPCoreProtocol["httpcore.ProtocolError"]
    end
    
    subgraph "Exception Mapping"
        ExceptionMap["HTTPCORE_EXC_MAP<br/>dynamic mapping dict"]
        MapContext["map_httpcore_exceptions()<br/>context manager"]
    end
    
    subgraph "httpx Exceptions"
        HTTPXTimeout["httpx.TimeoutException"]
        HTTPXConnect["httpx.ConnectError"]
        HTTPXRead["httpx.ReadError"] 
        HTTPXProtocol["httpx.ProtocolError"]
    end
    
    HTTPCoreTimeout --> ExceptionMap
    HTTPCoreConnect --> ExceptionMap
    HTTPCoreRead --> ExceptionMap
    HTTPCoreProtocol --> ExceptionMap
    
    ExceptionMap --> MapContext
    
    MapContext --> HTTPXTimeout
    MapContext --> HTTPXConnect
    MapContext --> HTTPXRead
    MapContext --> HTTPXProtocol
```

The mapping function `map_httpcore_exceptions()` is used as a context manager around `httpcore` operations to catch and re-raise exceptions with the appropriate `httpx` types.

**Sources:** [httpx/_transports/default.py:71-119]()

## Proxy Support

The transport architecture provides comprehensive proxy support through different `httpcore` backends. Proxy configuration is handled during transport initialization, with automatic selection of the appropriate backend.

```mermaid
graph TD
    subgraph "Proxy Configuration"
        ProxyURL["Proxy URL<br/>http://, https://, socks5://"]
        ProxyObject["Proxy object<br/>url, auth, headers, ssl_context"]
    end
    
    subgraph "Backend Selection"
        Decision{"Proxy Scheme?"}
        HTTPProxy["httpcore.HTTPProxy<br/>HTTP/HTTPS proxies"]
        SOCKSProxy["httpcore.SOCKSProxy<br/>SOCKS5 proxies"]
        DirectPool["httpcore.ConnectionPool<br/>no proxy"]
    end
    
    subgraph "Configuration Elements"
        ProxyAuth["proxy_auth<br/>raw bytes tuple"]
        ProxyHeaders["proxy_headers<br/>raw header list"]
        SSLContext["ssl_context<br/>for target connections"]
        ProxySSLContext["proxy_ssl_context<br/>for proxy connections"]
    end
    
    ProxyURL --> ProxyObject
    ProxyObject --> Decision
    
    Decision -->|"http/https"| HTTPProxy
    Decision -->|"socks5/socks5h"| SOCKSProxy  
    Decision -->|"None"| DirectPool
    
    ProxyObject --> ProxyAuth
    ProxyObject --> ProxyHeaders
    ProxyObject --> SSLContext
    ProxyObject --> ProxySSLContext
```

SOCKS proxy support requires the optional `socksio` dependency and is only available when `httpx` is installed with the `[socks]` extra.

**Sources:** [httpx/_transports/default.py:152-216](), [httpx/_transports/default.py:296-359](), [docs/troubleshooting.md:9-64]()

## Transport Configuration

Transport configuration combines connection limits, timeout settings, SSL contexts, and protocol options. The configuration flows from high-level client settings down to the `httpcore` backend.

```mermaid
graph TB
    subgraph "Configuration Classes"
        Limits["Limits<br/>max_connections<br/>max_keepalive_connections<br/>keepalive_expiry"]
        Timeout["Timeout<br/>connect, read, write, pool"]
        SSL["create_ssl_context()<br/>verify, cert, trust_env"]
        Proxy["Proxy<br/>url, auth, headers, ssl_context"]
    end
    
    subgraph "Protocol Settings"
        HTTP1["http1: bool<br/>enable HTTP/1.1"]
        HTTP2["http2: bool<br/>enable HTTP/2"]
        SocketOpts["socket_options<br/>low-level socket config"]
    end
    
    subgraph "Advanced Options"
        UDS["uds: str<br/>Unix domain socket"]
        LocalAddr["local_address: str<br/>bind to specific interface"]
        Retries["retries: int<br/>connection retry count"]
    end
    
    subgraph "httpcore Backend"
        Backend["ConnectionPool/<br/>HTTPProxy/<br/>SOCKSProxy"]
    end
    
    Limits --> Backend
    Timeout --> Backend
    SSL --> Backend
    Proxy --> Backend
    HTTP1 --> Backend
    HTTP2 --> Backend
    SocketOpts --> Backend
    UDS --> Backend
    LocalAddr --> Backend
    Retries --> Backend
```

**Sources:** [httpx/_transports/default.py:136-149](), [httpx/_transports/default.py:280-293](), [docs/advanced/transports.md:5-36]()

## Response Streaming

The transport layer handles response body streaming through wrapper classes (`ResponseStream` and `AsyncResponseStream`) that adapt `httpcore` streams to `httpx`'s streaming interfaces. This enables memory-efficient processing of large responses.

```mermaid
graph LR
    subgraph "Sync Streaming"
        HTTPCoreStream["httpcore stream<br/>Iterable[bytes]"]
        ResponseStream["ResponseStream<br/>SyncByteStream"]
        SyncClient["Client<br/>sync iteration"]
    end
    
    subgraph "Async Streaming"
        HTTPCoreAsyncStream["httpcore async stream<br/>AsyncIterable[bytes]"]
        AsyncResponseStream["AsyncResponseStream<br/>AsyncByteStream"]
        AsyncClient["AsyncClient<br/>async iteration"]
    end
    
    subgraph "Stream Operations"
        Iteration["__iter__() / __aiter__()<br/>chunk-by-chunk reading"]
        Closing["close() / aclose()<br/>resource cleanup"]
        ExceptionMapping["Exception mapping<br/>httpcore → httpx"]
    end
    
    HTTPCoreStream --> ResponseStream
    ResponseStream --> SyncClient
    HTTPCoreAsyncStream --> AsyncResponseStream
    AsyncResponseStream --> AsyncClient
    
    ResponseStream --> Iteration
    ResponseStream --> Closing
    ResponseStream --> ExceptionMapping
    
    AsyncResponseStream --> Iteration
    AsyncResponseStream --> Closing
    AsyncResponseStream --> ExceptionMapping
```

The streaming classes provide automatic resource cleanup and exception mapping while preserving the streaming semantics from the underlying engine.

**Sources:** [httpx/_transports/default.py:121-133](), [httpx/_transports/default.py:265-277]()

## httpcore Integration

The transport architecture serves as an adapter layer between `httpx`'s high-level API and `httpcore`'s low-level HTTP implementation. This integration handles format conversion, configuration mapping, and lifecycle management.

```mermaid
graph TB
    subgraph "httpx Layer"
        HTTPXRequest["httpx.Request<br/>method, url, headers, stream"]
        HTTPXResponse["httpx.Response<br/>status_code, headers, stream"]
        HTTPXConfig["httpx Configuration<br/>Timeout, Limits, Proxy"]
    end
    
    subgraph "Conversion Layer"
        RequestConversion["Request Conversion<br/>httpx → httpcore format"]
        ResponseConversion["Response Conversion<br/>httpcore → httpx format"]
        ConfigMapping["Config Mapping<br/>httpx → httpcore params"]
    end
    
    subgraph "httpcore Layer"
        HTTPCoreRequest["httpcore.Request<br/>method, url, headers, content"]
        HTTPCoreResponse["httpcore.Response<br/>status, headers, stream"]
        HTTPCorePool["httpcore Pool<br/>ConnectionPool/Proxy"]
    end
    
    HTTPXRequest --> RequestConversion
    RequestConversion --> HTTPCoreRequest
    HTTPCoreRequest --> HTTPCorePool
    HTTPCorePool --> HTTPCoreResponse
    HTTPCoreResponse --> ResponseConversion
    ResponseConversion --> HTTPXResponse
    
    HTTPXConfig --> ConfigMapping
    ConfigMapping --> HTTPCorePool
```

The integration handles several key transformations:

| Component | httpx Format | httpcore Format | Purpose |
|-----------|--------------|-----------------|---------|
| URL | `httpx.URL` | `httpcore.URL` | URL parsing and validation |
| Headers | `httpx.Headers` | Raw header list | Header manipulation |
| Body | `SyncByteStream`/`AsyncByteStream` | Stream interface | Content streaming |
| Extensions | Request metadata dict | Extensions dict | Protocol-specific data |

**Sources:** [httpx/_transports/default.py:237-259](), [httpx/_transports/default.py:381-403]()

---

# Page: ASGI and WSGI Integration

# ASGI and WSGI Integration

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_transports/asgi.py](httpx/_transports/asgi.py)
- [httpx/_transports/wsgi.py](httpx/_transports/wsgi.py)
- [tests/test_asgi.py](tests/test_asgi.py)
- [tests/test_wsgi.py](tests/test_wsgi.py)

</details>



HTTPX provides transport classes for direct integration with ASGI and WSGI applications, enabling HTTP requests without network transport. This allows testing web applications and mocking services by bypassing the network layer and avoiding the overhead of socket communication.

## Overview

HTTPX includes two transport implementations for direct application integration:

- `WSGITransport` - Handles synchronous WSGI applications (e.g., Flask, Django). [httpx/_transports/wsgi.py:44-46]()
- `ASGITransport` - Handles asynchronous ASGI applications (e.g., FastAPI, Starlette). [httpx/_transports/asgi.py:63-65]()

These transports implement the `BaseTransport` and `AsyncBaseTransport` interfaces, converting HTTPX `Request` objects to application-specific formats and converting application responses back to HTTPX `Response` objects.

### Transport Architecture Overview

```mermaid
flowchart TD
    Client["httpx.Client"]
    AsyncClient["httpx.AsyncClient"]
    
    subgraph "Transport Layer"
        WSGITransport["WSGITransport"]
        ASGITransport["ASGITransport"]
        HTTPTransport["HTTPTransport"]
    end
    
    subgraph "Application Layer"
        WSGIApp["WSGIApplication"]
        ASGIApp["_ASGIApp"]
        NetworkAPI["Network HTTP API"]
    end
    
    subgraph "Response Streams"
        WSGIByteStream["WSGIByteStream"]
        ASGIResponseStream["ASGIResponseStream"]
    end
    
    Client -->|"handle_request()"| WSGITransport
    AsyncClient -->|"handle_async_request()"| ASGITransport
    Client -->|"handle_request()"| HTTPTransport
    
    WSGITransport -->|"app(environ, start_response)"| WSGIApp
    ASGITransport -->|"await app(scope, receive, send)"| ASGIApp
    HTTPTransport --> NetworkAPI
    
    WSGITransport --> WSGIByteStream
    ASGITransport --> ASGIResponseStream
```

Sources: [httpx/_transports/wsgi.py:44-149](), [httpx/_transports/asgi.py:63-187](), [httpx/_transports/base.py:14-86]()

## WSGI Integration

### WSGITransport Implementation

The `WSGITransport` class extends `BaseTransport` and implements `handle_request()` for synchronous WSGI applications. It converts the `httpx.Request` into a WSGI `environ` dictionary and provides a `start_response` callback. [httpx/_transports/wsgi.py:91-149]()

### WSGITransport Request Processing

```mermaid
sequenceDiagram
    participant Client as "httpx.Client"
    participant WSGITransport as "WSGITransport"
    participant WSGIApplication as "WSGIApplication (app)"
    participant start_response as "start_response (callback)"
    
    Client->>WSGITransport: "handle_request(request)"
    WSGITransport->>WSGITransport: "request.read()"
    WSGITransport->>WSGITransport: "Build WSGI environ dict"
    WSGITransport->>WSGIApplication: "app(environ, start_response)"
    WSGIApplication->>start_response: "start_response(status, headers, exc_info)"
    WSGIApplication-->>WSGITransport: "yield response chunks (Iterable[bytes])"
    WSGITransport->>WSGITransport: "WSGIByteStream(result)"
    WSGITransport-->>Client: "Response(status_code, headers, stream)"
```

Sources: [httpx/_transports/wsgi.py:91-149]()

### WSGITransport Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `app` | `WSGIApplication` | Required | The WSGI application callable. [httpx/_transports/wsgi.py:79]() |
| `raise_app_exceptions` | `bool` | `True` | Whether to raise exceptions occurring within the application. [httpx/_transports/wsgi.py:80]() |
| `script_name` | `str` | `""` | The WSGI `SCRIPT_NAME` environment variable. [httpx/_transports/wsgi.py:81]() |
| `remote_addr` | `str` | `"127.0.0.1"` | The WSGI `REMOTE_ADDR` environment variable. [httpx/_transports/wsgi.py:82]() |
| `wsgi_errors` | `typing.TextIO \| None` | `None` | The stream for `wsgi.errors` (defaults to `sys.stderr`). [httpx/_transports/wsgi.py:83]() |

Sources: [httpx/_transports/wsgi.py:77-90]()

### Example Usage

```python
import httpx

# Synchronous usage with WSGI
transport = httpx.WSGITransport(app=my_wsgi_app)
with httpx.Client(transport=transport) as client:
    response = client.get("http://testserver/")
```

Sources: [tests/test_wsgi.py:94-99]()

## ASGI Integration

### ASGITransport Implementation

The `ASGITransport` class extends `AsyncBaseTransport` and implements `handle_async_request()` for asynchronous ASGI applications. It maps the `httpx.Request` to an ASGI `scope` and manages the `receive` and `send` awaitables to communicate with the application. [httpx/_transports/asgi.py:99-187]()

### ASGITransport Request Processing

```mermaid
sequenceDiagram
    participant AsyncClient as "httpx.AsyncClient"
    participant ASGITransport as "ASGITransport"
    participant _ASGIApp as "ASGI App (app)"
    participant _Receive as "receive() (awaitable)"
    participant _Send as "send() (awaitable)"
    
    AsyncClient->>ASGITransport: "handle_async_request(request)"
    ASGITransport->>ASGITransport: "Build ASGI scope dict"
    ASGITransport->>ASGITransport: "Define receive() and send()"
    ASGITransport->>_ASGIApp: "await app(scope, receive, send)"
    _ASGIApp->>_Send: "await send({'type': 'http.response.start', ...})"
    _ASGIApp->>_Send: "await send({'type': 'http.response.body', ...})"
    _ASGIApp->>_Receive: "await receive() (request body chunks)"
    ASGITransport->>ASGITransport: "ASGIResponseStream(body_parts)"
    ASGITransport-->>AsyncClient: "Response(status_code, headers, stream)"
```

Sources: [httpx/_transports/asgi.py:99-187]()

### ASGITransport Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `app` | `_ASGIApp` | Required | The ASGI application callable. [httpx/_transports/asgi.py:89]() |
| `raise_app_exceptions` | `bool` | `True` | Whether to raise application exceptions. [httpx/_transports/asgi.py:90]() |
| `root_path` | `str` | `""` | The ASGI `root_path` scope variable. [httpx/_transports/asgi.py:91]() |
| `client` | `tuple[str, int]` | `("127.0.0.1", 123)` | The ASGI `client` (IP, port) scope variable. [httpx/_transports/asgi.py:92]() |

Sources: [httpx/_transports/asgi.py:87-97]()

### Example Usage

```python
import httpx

# Asynchronous usage with ASGI
transport = httpx.ASGITransport(app=my_asgi_app)
async with httpx.AsyncClient(transport=transport) as client:
    response = await client.get("http://testserver/")
```

Sources: [tests/test_asgi.py:94-100]()

## Class Architecture

### Transport Class Hierarchy

```mermaid
classDiagram
    class AsyncBaseTransport {
        <<interface>>
        +handle_async_request(request: Request) Response
    }
    class BaseTransport {
        <<interface>>
        +handle_request(request: Request) Response
    }
    class ASGITransport {
        +app: _ASGIApp
        +handle_async_request(request: Request) Response
        -receive() _Message
        -send(message: _Message)
    }
    class WSGITransport {
        +app: WSGIApplication
        +handle_request(request: Request) Response
        -start_response(status, headers, exc_info)
    }
    class ASGIResponseStream {
        +__aiter__() AsyncIterator[bytes]
    }
    class WSGIByteStream {
        +__iter__() Iterator[bytes]
    }

    AsyncBaseTransport <|-- ASGITransport
    BaseTransport <|-- WSGITransport
    ASGITransport ..> ASGIResponseStream : creates
    WSGITransport ..> WSGIByteStream : creates
```

Sources: [httpx/_transports/asgi.py:55-187](), [httpx/_transports/wsgi.py:30-149](), [httpx/_transports/base.py:14-86]()

## Implementation Details

### ASGI Scope and WSGI Environ Construction

The transports map HTTPX request attributes to the standard interface dictionaries:

| Field | ASGITransport (Scope) | WSGITransport (Environ) |
|-------|-----------------------|-------------------------|
| Method | `scope["method"]` [httpx/_transports/asgi.py:110]() | `environ["REQUEST_METHOD"]` [httpx/_transports/wsgi.py:104]() |
| Path | `scope["path"]` [httpx/_transports/asgi.py:113]() | `environ["PATH_INFO"]` [httpx/_transports/wsgi.py:106]() |
| Query | `scope["query_string"]` [httpx/_transports/asgi.py:115]() | `environ["QUERY_STRING"]` [httpx/_transports/wsgi.py:107]() |
| Host | `scope["server"]` [httpx/_transports/asgi.py:116]() | `environ["SERVER_NAME"]` [httpx/_transports/wsgi.py:108]() |
| Port | `scope["server"]` [httpx/_transports/asgi.py:116]() | `environ["SERVER_PORT"]` [httpx/_transports/wsgi.py:109]() |
| Headers | `scope["headers"]` [httpx/_transports/asgi.py:111]() | `environ["HTTP_*"]` [httpx/_transports/wsgi.py:116]() |

### Exception Handling

Both transports provide a mechanism to catch or propagate application exceptions via the `raise_app_exceptions` flag. 

- In `WSGITransport`, if an exception is passed to `start_response` and `raise_app_exceptions` is `True`, the exception is re-raised. [httpx/_transports/wsgi.py:140-141]()
- In `ASGITransport`, if the `await self.app(...)` call raises an exception and `raise_app_exceptions` is `True`, it propagates. Otherwise, a 500 status code is returned. [httpx/_transports/asgi.py:171-180]()

### Stream Handling

- **WSGI**: Uses `WSGIByteStream`, which wraps the iterable returned by the WSGI application and handles closing the iterable if a `.close()` method is present. [httpx/_transports/wsgi.py:30-42]()
- **ASGI**: Uses `ASGIResponseStream`, which collects body parts received via the `http.response.body` message and yields them as a single joined byte string. [httpx/_transports/asgi.py:55-61]()

Sources: [httpx/_transports/asgi.py:169-187](), [httpx/_transports/wsgi.py:136-149]()

---

# Page: Proxy Support

# Proxy Support

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [docs/advanced/proxies.md](docs/advanced/proxies.md)
- [docs/contributing.md](docs/contributing.md)
- [docs/http2.md](docs/http2.md)
- [httpx/_config.py](httpx/_config.py)
- [httpx/_utils.py](httpx/_utils.py)
- [tests/client/test_proxies.py](tests/client/test_proxies.py)
- [tests/test_utils.py](tests/test_utils.py)

</details>



This page documents the proxy support system in HTTPX, which allows HTTP requests to be routed through proxy servers. The proxy system enables configuring proxy servers through direct client configuration and environment variables, with support for HTTP, HTTPS, and SOCKS proxies.

For information about ASGI and WSGI application testing, see [ASGI and WSGI Integration](#5.2).

## Proxy Configuration

HTTPX allows you to configure proxies in several ways:

1. Directly on a client instance using the `proxy` parameter.
2. Through environment variables (`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY`).
3. Using URL-specific proxy routing via the `mounts` dictionary.

When a request is made, HTTPX determines if a proxy should be used based on the request URL and configured proxy settings.

```python
# Direct proxy configuration
client = httpx.Client(proxy="http://proxy.example.com:8080")

# URL-specific proxy routing using mounts
client = httpx.Client(mounts={
    "http://": httpx.HTTPTransport(proxy="http://localhost:8030"),
    "https://": httpx.HTTPTransport(proxy="http://localhost:8031"),
    "all://internal.example.com": None  # Bypass proxy for this host
})
```

Sources: [docs/advanced/proxies.md:1-27](), [httpx/_config.py:201-244]()

## Proxy Class

The `Proxy` class in HTTPX encapsulates the configuration for a proxy server. This class handles proxy URL parsing, authentication credentials, and custom headers.

```mermaid
classDiagram
    class Proxy {
        +URL url
        +tuple|None auth
        +Headers headers
        +SSLContext|None ssl_context
        +__init__(url, ssl_context, auth, headers)
    }
    Proxy o-- "httpx.URL" : uses
    Proxy o-- "httpx.Headers" : uses
```

The `Proxy` class validates that the proxy URL scheme is one of the supported types: `http`, `https`, `socks5`, or `socks5h`. Authentication credentials provided in the URL (e.g., `http://user:pass@host`) are extracted during initialization.

Sources: [httpx/_config.py:201-244](), [docs/advanced/proxies.md:38-46]()

## Proxy URL Patterns

HTTPX uses a pattern matching system to determine which proxy to use for a given request URL. This is implemented in the `URLPattern` class.

```mermaid
classDiagram
    class URLPattern {
        +str pattern
        +str scheme
        +str host
        +int|None port
        +Pattern|None host_regex
        +matches(URL other) bool
    }
```

URL patterns support several matching features:
- **Scheme matching**: Match specific schemes like `http://` or `https://`. [httpx/_utils.py:129-134]()
- **Wildcard scheme**: `all://` matches any scheme. [httpx/_utils.py:125-127]()
- **Domain matching**: Match specific domains or subdomains. [httpx/_utils.py:137-144]()
- **Wildcard domains**: `*.example.com` matches subdomains (e.g., `www.example.com`) but not the domain itself. [httpx/_utils.py:179-182]()
- **Port matching**: Match specific ports. [httpx/_utils.py:155-160]()

Patterns are prioritized by specificity. For example, `http://example.com:123` has higher priority than `http://example.com`, which in turn is higher than `http://`. [tests/test_utils.py:137-151]()

Sources: [httpx/_utils.py:120-203](), [tests/test_utils.py:115-151]()

## Environment Variables Support

The function `get_environment_proxies()` reads proxy configuration from standard environment variables, facilitating compatibility with system-wide settings.

| Environment Variable | Description | Pattern Mapping |
|---------------------|-------------|-----------------|
| `HTTP_PROXY` | Proxy for HTTP requests | `http://` |
| `HTTPS_PROXY` | Proxy for HTTPS requests | `https://` |
| `ALL_PROXY` | Proxy for all requests | `all://` |
| `NO_PROXY` | Bypass proxy for these hosts | `all://*host` |

The `NO_PROXY` variable is handled with specific logic:
- A value of `*` bypasses all proxies. [httpx/_utils.py:51-56]()
- Domain names like `google.com` match the domain and subdomains (`all://*google.com`). [httpx/_utils.py:73-74]()
- Domain names starting with a dot like `.google.com` match subdomains only (`all://*.google.com`). [httpx/_utils.py:179-182]()
- IP addresses and `localhost` are mapped to specific `all://` patterns. [httpx/_utils.py:67-72]()

Sources: [httpx/_utils.py:30-76](), [tests/test_utils.py:89-112]()

## Different Proxy Types

### HTTP/HTTPS Proxies
Standard HTTP proxies are supported natively. In most cases, the proxy URL for the `https://` key should use the `http://` scheme, as most proxies handle HTTPS via the `CONNECT` method (Tunnelling) over an unencrypted connection to the proxy. [docs/advanced/proxies.md:31-37]()

### SOCKS Proxies
SOCKS5 support is an optional feature requiring the `socksio` library. [docs/advanced/proxies.md:68-72]()
- `socks5://`: Remote DNS resolution.
- `socks5h://`: Local DNS resolution. [tests/client/test_proxies.py:16-29]()

Sources: [docs/advanced/proxies.md:68-84](), [tests/client/test_proxies.py:16-29]()

## Proxy Selection Process

When a client performs a request, it selects the appropriate transport (and thus the proxy) using the `_transport_for_url` method (internal logic).

```mermaid
flowchart TD
    Start(["Request to URL"]) --> CheckMounts{"Matches 'mounts'?"}
    CheckMounts -- "Yes" --> UseMount["Use specific Transport from mounts"]
    CheckMounts -- "No" --> CheckProxyParam{"'proxy' param set?"}
    CheckProxyParam -- "Yes" --> UseProxy["Use Client proxy"]
    CheckProxyParam -- "No" --> CheckEnv{"'trust_env' is True?"}
    CheckEnv -- "Yes" --> GetEnv["Load from Environment Vars"]
    CheckEnv -- "No" --> Direct["Direct Connection"]
    GetEnv --> MatchEnv{"URL matches Env Proxy?"}
    MatchEnv -- "Yes" --> UseEnv["Use Environment Proxy"]
    MatchEnv -- "No" --> Direct
```

Sources: [tests/client/test_proxies.py:34-100](), [httpx/_utils.py:192-203]()

## Usage Examples

### Forwarding vs Tunnelling
- **Forwarding**: The proxy makes the request and returns the response. [docs/advanced/proxies.md:61]()
- **Tunnelling**: The proxy establishes a TCP connection (HTTP Tunnel) to the server; the client then performs the TLS handshake directly with the destination server. [docs/advanced/proxies.md:62]()

### Routing with Mounts
Mounts allow for complex routing rules. If a value in the mounts dictionary is `None`, the proxy is bypassed for that pattern. [tests/client/test_proxies.py:88-100]()

```python
mounts = {
    "all://": httpx.HTTPTransport(proxy="http://localhost:8030"),
    "all://*.internal.com": None  # Bypass proxy for internal subdomains
}
client = httpx.Client(mounts=mounts)
```

Sources: [docs/advanced/proxies.md:17-27](), [tests/client/test_proxies.py:88-100]()

---

# Page: Mock Transports

# Mock Transports

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_transports/base.py](httpx/_transports/base.py)
- [httpx/_transports/mock.py](httpx/_transports/mock.py)
- [tests/client/test_async_client.py](tests/client/test_async_client.py)
- [tests/client/test_client.py](tests/client/test_client.py)

</details>



Mock transports provide a way to intercept HTTP requests and return custom responses without making actual network calls. They are primarily used for testing, allowing you to simulate various server responses, network conditions, and edge cases. Mock transports can also be used for custom request handling scenarios where you need fine-grained control over the request-response cycle.

For information about other transport types, see [Transport Architecture](#5.1), [ASGI and WSGI Integration](#5.2), and [Proxy Support](#5.3).

## MockTransport Architecture

The `MockTransport` class implements both synchronous and asynchronous transport interfaces, allowing it to work with both `Client` and `AsyncClient` instances [httpx/_transports/mock.py:15](). It accepts a handler function that processes incoming requests and generates responses.

### Code Entity Space: MockTransport Hierarchy

```mermaid
graph TB
    subgraph "httpx._transports.base"
        BaseTransport["BaseTransport"]
        AsyncBaseTransport["AsyncBaseTransport"]
    end

    subgraph "httpx._transports.mock"
        MockTransport["MockTransport"]
        SyncHandler["SyncHandler (TypeAlias)"]
        AsyncHandler["AsyncHandler (TypeAlias)"]
    end
    
    BaseTransport --> MockTransport
    AsyncBaseTransport --> MockTransport
    
    MockTransport -.-> SyncHandler
    MockTransport -.-> AsyncHandler
```

Sources: [httpx/_transports/mock.py:8-16](), [httpx/_transports/base.py:14-87]()

## Handler Function Interface

Mock transport handlers receive a `httpx.Request` object and must return a `httpx.Response` object [httpx/_transports/mock.py:8-9](). The handler can be either a synchronous function or an asynchronous coroutine.

### Data Flow: Request Handling

```mermaid
sequenceDiagram
    participant C as httpx.Client / httpx.AsyncClient
    participant M as httpx.MockTransport
    participant H as Handler Function

    C->>M: handle_request() / handle_async_request()
    
    alt Synchronous Path
        M->>M: request.read()
        M->>H: handler(request)
        H-->>M: httpx.Response
    else Asynchronous Path
        M->>M: await request.aread()
        M->>H: handler(request)
        opt if Coroutine
            H-->>M: await result
        end
        H-->>M: httpx.Response
    end

    M-->>C: httpx.Response
```

The `MockTransport` class handles the differences between synchronous and asynchronous execution automatically:

- **Sync mode**: Calls `request.read()` [httpx/_transports/mock.py:23]() to ensure the request body is loaded, then invokes the handler. It raises a `TypeError` if an async handler is provided to a sync client [httpx/_transports/mock.py:25-26]().
- **Async mode**: Calls `await request.aread()` [httpx/_transports/mock.py:33]() and can handle both sync and async handler functions by checking if the result is an instance of `Response` [httpx/_transports/mock.py:40-41]().

Sources: [httpx/_transports/mock.py:19-43]()

## Creating Mock Handlers

### Synchronous Handlers

Synchronous handlers are simple functions that take a `Request` and return a `Response`. These are defined by the `SyncHandler` type [httpx/_transports/mock.py:8]().

```python
def simple_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, content=b"Mock response")

def echo_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200, 
        headers={"content-type": "application/json"},
        content=request.content
    )
```

### Asynchronous Handlers

Async handlers can perform asynchronous operations and return responses. These are defined by the `AsyncHandler` type [httpx/_transports/mock.py:9]().

```python
async def async_handler(request: httpx.Request) -> httpx.Response:
    # Simulate async processing
    await asyncio.sleep(0.1)
    return httpx.Response(200, content=b"Async mock response")
```

Sources: [httpx/_transports/mock.py:8-10]()

## Usage with Clients

### Synchronous Client Usage

When used with `httpx.Client`, the transport calls `handle_request` [httpx/_transports/mock.py:19]().

```python
import httpx

def mock_handler(request):
    if request.url.path == "/users":
        return httpx.Response(200, json={"users": []})
    return httpx.Response(404, text="Not found")

transport = httpx.MockTransport(mock_handler)
with httpx.Client(transport=transport) as client:
    response = client.get("http://example.com/users")
    assert response.status_code == 200
```

### Asynchronous Client Usage

When used with `httpx.AsyncClient`, the transport calls `handle_async_request` [httpx/_transports/mock.py:29]().

```python
import httpx

async def async_mock_handler(request):
    return httpx.Response(200, json={"async": True})

transport = httpx.MockTransport(async_mock_handler)
async with httpx.AsyncClient(transport=transport) as client:
    response = await client.get("http://example.com/")
    assert response.json() == {"async": True}
```

Sources: [httpx/_transports/mock.py:19-43](), [tests/client/test_client.py:18-19](), [tests/client/test_async_client.py:14-15]()

## Request Processing Logic

The internal logic of `MockTransport` ensures that the request is fully consumed before the handler sees it.

### Code Logic: MockTransport.handle_async_request

```mermaid
graph TD
    Start["Call handle_async_request(request)"] --> Aread["await request.aread()"]
    Aread --> Call["response = self.handler(request)"]
    Call --> Check{"isinstance(response, Response)?"}
    Check -- "No" --> AwaitResp["response = await response"]
    Check -- "Yes" --> Return["return response"]
    AwaitResp --> Return
```

The transport ensures that:
1. Request bodies are fully read via `read()` or `aread()` before passing to handlers [httpx/_transports/mock.py:23,33]().
2. Sync handlers work with both sync and async clients [httpx/_transports/mock.py:40]().
3. Async handlers are awaited only in the async request path [httpx/_transports/mock.py:41]().

Sources: [httpx/_transports/mock.py:19-43]()

## Testing Patterns

### Status Code Testing
Handlers can inspect the `request.url.path` to simulate different server behaviors [tests/client/test_client.py:137-139]().

```python
def status_handler(request):
    path = request.url.path
    if path == "/404":
        return httpx.Response(404)
    return httpx.Response(200)
```

### Header Testing
Handlers can return custom `httpx.Headers` to test client-side header parsing [tests/client/test_client.py:49-53]().

```python
def header_handler(request):
    return httpx.Response(200, headers={"X-Test": "Value"})
```

### Request Inspection
Since the `Request` object is passed to the handler, you can perform assertions directly inside the mock [tests/client/test_client.py:59,75]().

```python
def inspection_handler(request):
    assert request.method == "POST"
    assert request.headers["Content-Type"] == "application/json"
    return httpx.Response(200)
```

Sources: [httpx/_transports/mock.py:19-43](), [tests/client/test_client.py:47-76]()

## Error Handling

Mock handlers can raise exceptions or return error responses. If a handler raises an exception, it propagates through the transport to the client call site.

```python
def error_handler(request):
    if request.url.path == "/timeout":
        raise httpx.ReadTimeout("Mock timeout", request=request)
    return httpx.Response(200)
```

For controlled HTTP errors, it is recommended to return a `httpx.Response` with a 4xx or 5xx status code and allow the client to call `response.raise_for_status()` [tests/client/test_client.py:141-142]().

Sources: [httpx/_transports/mock.py:19-27](), [tests/client/test_client.py:134-147]()

---

# Page: Configuration

# Configuration

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_config.py](httpx/_config.py)
- [tests/test_api.py](tests/test_api.py)
- [tests/test_config.py](tests/test_config.py)
- [tests/test_timeouts.py](tests/test_timeouts.py)

</details>



This page documents the configuration system in HTTPX, explaining how to customize client behavior through timeouts, connection limits, SSL/TLS settings, and proxy configuration. These settings can be applied globally at the `Client` level or overridden for individual requests.

## Overview

HTTPX provides several configuration classes defined in [httpx/_config.py](httpx/_config.py) that encapsulate specific domains of client behavior:

| Class | Purpose | Key Parameters |
|-------|---------|----------------|
| `Timeout` | Controls network operation timeouts | `connect`, `read`, `write`, `pool` |
| `Limits` | Manages connection pooling and concurrency | `max_connections`, `max_keepalive_connections`, `keepalive_expiry` |
| `Proxy` | Configures proxy server routing | `url`, `auth`, `headers`, `ssl_context` |

### Configuration Class Architecture

The following diagram shows how configuration classes are defined and where they are consumed within the library.

```mermaid
flowchart TD
    subgraph "Configuration Definitions [_config.py]"
        TimeoutClass["Timeout
        [lines 72-156]"]
        LimitsClass["Limits
        [lines 159-198]"]
        ProxyClass["Proxy
        [lines 201-243]"]
        create_ssl_context["create_ssl_context()
        [lines 23-69]"]
    end
    
    subgraph "Client Layer [_client.py]"
        Client["Client class"]
        AsyncClient["AsyncClient class"]
    end
    
    subgraph "API Layer [_api.py]"
        request_func["request()"]
        get_func["get()"]
    end
    
    subgraph "Transport Layer [_transports/default.py]"
        HTTPTransport["HTTPTransport
        [lines 135-216]"]
        AsyncHTTPTransport["AsyncHTTPTransport
        [lines 279-360]"]
    end
    
    TimeoutClass --> Client
    TimeoutClass --> request_func
    
    LimitsClass --> HTTPTransport
    LimitsClass --> AsyncHTTPTransport
    
    ProxyClass --> HTTPTransport
    ProxyClass --> AsyncHTTPTransport
    
    create_ssl_context --> HTTPTransport
    
    Client --> HTTPTransport
    AsyncClient --> AsyncHTTPTransport
```

Sources: [httpx/_config.py:1-243](), [httpx/_transports/default.py:135-360](), [httpx/_api.py:1-439]()

## Default Configuration Values

HTTPX defines sensible defaults for common configurations to ensure safe out-of-the-box behavior.

| Configuration | Default Value | File Reference |
|---------------|---------------|----------|
| `DEFAULT_TIMEOUT_CONFIG` | `Timeout(timeout=5.0)` | [httpx/_config.py:246]() |
| `DEFAULT_LIMITS` | `Limits(max_connections=100, max_keepalive_connections=20)` | [httpx/_config.py:247]() |
| `DEFAULT_MAX_REDIRECTS` | `20` | [httpx/_config.py:248]() |

Sources: [httpx/_config.py:246-248]()

## Timeouts

The `Timeout` class manages granular control over how long the client should wait for various network operations. By default, HTTPX includes a 5-second timeout for all operations [httpx/_config.py:246]().

### Timeout Types
- **Connect**: Time to establish a socket connection.
- **Read**: Time to receive a chunk of data from the server.
- **Write**: Time to send a chunk of data to the server.
- **Pool**: Time to wait for a connection to become available in the pool.

For details, see [Timeouts](#6.1).

Sources: [httpx/_config.py:72-156](), [tests/test_timeouts.py:7-56]()

## Connection Limits

The `Limits` class controls the connection pool size and keep-alive behavior. This is essential for managing resource usage when making many concurrent requests.

- **max_connections**: Total number of allowed concurrent connections [httpx/_config.py:180]().
- **max_keepalive_connections**: Number of idle connections kept open for reuse [httpx/_config.py:181]().
- **keepalive_expiry**: Duration in seconds to keep an idle connection alive [httpx/_config.py:182]().

For details, see [Connection Limits](#6.2).

Sources: [httpx/_config.py:159-198](), [httpx/_transports/default.py:156-167]()

## SSL and Security

SSL/TLS configuration is primarily handled via `create_ssl_context()` [httpx/_config.py:23](). This function manages certificate verification, client-side certificates, and integration with system trust stores or environment variables like `SSL_CERT_FILE` [httpx/_config.py:34-37]().

For details, see [SSL and Security](#6.3).

Sources: [httpx/_config.py:23-69](), [tests/test_config.py:11-86]()

## Event Hooks

HTTPX features an event hook system that allows you to register callbacks for specific points in the request/response lifecycle. Hooks are typically used for logging, monitoring, or modifying responses globally.

For details, see [Event Hooks](#6.4).

Sources: [httpx/_client.py:1-200]() (Note: hooks are initialized in Client classes)

## Command Line Interface

HTTPX includes a CLI tool that exposes the library's configuration options through command-line arguments. This allows for quick testing of timeouts, proxies, and SSL settings without writing Python code.

For details, see [Command Line Interface](#6.5).

Sources: [httpx/_main.py:393-429]()

## Configuration Mapping

The following diagram bridges the high-level configuration parameters to the internal `httpcore` entities they eventually configure.

```mermaid
graph LR
    subgraph "HTTPX Configuration"
        T[httpx.Timeout]
        L[httpx.Limits]
        P[httpx.Proxy]
    end

    subgraph "Internal Transport [_transports/default.py]"
        HT[HTTPTransport]
    end

    subgraph "httpcore Entities"
        CP["httpcore.ConnectionPool
        [lines 156-167]"]
        HP["httpcore.HTTPProxy
        [lines 168-186]"]
        SP["httpcore.SOCKSProxy
        [lines 187-210]"]
    end

    T --> HT
    L --> HT
    P --> HT
    
    HT --> CP
    HT --> HP
    HT --> SP
```

Sources: [httpx/_transports/default.py:156-210](), [httpx/_config.py:1-243]()

---

# Page: Timeouts

# Timeouts

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [docs/advanced/authentication.md](docs/advanced/authentication.md)
- [docs/advanced/event-hooks.md](docs/advanced/event-hooks.md)
- [docs/advanced/resource-limits.md](docs/advanced/resource-limits.md)
- [docs/advanced/text-encodings.md](docs/advanced/text-encodings.md)
- [docs/advanced/timeouts.md](docs/advanced/timeouts.md)
- [httpx/_config.py](httpx/_config.py)
- [tests/test_api.py](tests/test_api.py)
- [tests/test_config.py](tests/test_config.py)
- [tests/test_timeouts.py](tests/test_timeouts.py)

</details>



This document covers httpx's timeout configuration system, which provides fine-grained control over network operation timeouts. Timeouts prevent requests from hanging indefinitely when network conditions are poor or servers are unresponsive.

For information about connection limits and pooling behavior, see [Connection Limits](#6.2). For SSL/TLS configuration, see [SSL and Security](#6.3).

## Overview

`httpx` is careful to enforce timeouts everywhere by default. The default behavior is to raise a `TimeoutException` after 5 seconds of network inactivity [docs/advanced/timeouts.md:1-4]().

The timeout system is built around the `Timeout` class in [httpx/_config.py:72-157]() and supports both simple scalar values and detailed per-operation configuration.

### Timeout Architecture

```mermaid
graph TB
    subgraph "Client Configuration"
        ClientTimeout["Client timeout parameter<br/>TimeoutTypes"]
        DefaultTimeout["DEFAULT_TIMEOUT_CONFIG<br/>Timeout(5.0)"]
    end
    
    subgraph "Timeout Class System"
        TimeoutClass["httpx.Timeout class<br/>_config.py:72"]
        ConnectTimeout["connect: Optional[float]<br/>Connection establishment"]
        ReadTimeout["read: Optional[float]<br/>Reading response data"]
        WriteTimeout["write: Optional[float]<br/>Writing request data"]
        PoolTimeout["pool: Optional[float]<br/>Acquiring connection"]
    end
    
    subgraph "Transport Integration"
        HTTPTransport["HTTPTransport<br/>_transports/default.py:135"]
        HttpCorePool["httpcore.ConnectionPool<br/>External Dependency"]
        NetworkOps["Network Operations<br/>Socket I/O"]
    end
    
    subgraph "Exception Handling"
        TimeoutExceptions["Timeout Exceptions<br/>ConnectTimeout, ReadTimeout<br/>WriteTimeout, PoolTimeout"]
    end
    
    ClientTimeout --> TimeoutClass
    DefaultTimeout --> TimeoutClass
    TimeoutClass --> ConnectTimeout
    TimeoutClass --> ReadTimeout
    TimeoutClass --> WriteTimeout
    TimeoutClass --> PoolTimeout
    
    TimeoutClass --> HTTPTransport
    HTTPTransport --> HttpCorePool
    HttpCorePool --> NetworkOps
    NetworkOps --> TimeoutExceptions
```

Sources: [httpx/_config.py:72-157](), [docs/advanced/timeouts.md:1-4](), [httpx/_transports/default.py:135-216]()

## Timeout Types

httpx distinguishes between four timeout operations, each serving a specific purpose in the HTTP request lifecycle [docs/advanced/timeouts.md:43-61]():

| Timeout Type | Purpose | Typical Use Case |
|--------------|---------|------------------|
| `connect` | Time limit for establishing TCP connection | Detect unreachable hosts |
| `read` | Time limit for receiving response data | Detect slow or stalled responses |
| `write` | Time limit for sending request data | Detect slow upload conditions |
| `pool` | Time limit for acquiring connection from pool | Prevent indefinite waiting when pool is exhausted |

### Timeout Class Implementation

The `Timeout` class handles various input formats, including scalar floats, tuples, or keyword arguments [httpx/_config.py:86-131]().

```mermaid
graph LR
    subgraph "Timeout Construction"
        ScalarInput["Scalar: 5.0<br/>TimeoutTypes"]
        TupleInput["Tuple: (5.0, 3.0, None, 1.0)<br/>TimeoutTypes"]
        TimeoutInput["Timeout object<br/>TimeoutTypes"]
        KeywordInput["Keywords: connect=5.0<br/>read=3.0, etc."]
    end
    
    subgraph "Timeout Class"
        TimeoutInit["Timeout.__init__<br/>_config.py:86"]
        ConnectAttr["self.connect"]
        ReadAttr["self.read"] 
        WriteAttr["self.write"]
        PoolAttr["self.pool"]
    end
    
    subgraph "Validation & Processing"
        UnsetHandling["UNSET value handling<br/>_config.py:20"]
        AsDict["as_dict() method<br/>_config.py:132"]
        Repr["__repr__ method<br/>_config.py:149"]
    end
    
    ScalarInput --> TimeoutInit
    TupleInput --> TimeoutInit
    TimeoutInput --> TimeoutInit
    KeywordInput --> TimeoutInit
    
    TimeoutInit --> ConnectAttr
    TimeoutInit --> ReadAttr
    TimeoutInit --> WriteAttr
    TimeoutInit --> PoolAttr
    
    TimeoutInit --> UnsetHandling
    ConnectAttr --> AsDict
    ReadAttr --> AsDict
    WriteAttr --> AsDict
    PoolAttr --> AsDict
    
    AsDict --> Repr
```

Sources: [httpx/_config.py:86-157](), [httpx/_config.py:16-21](), [httpx/_types.py:7]()

## Configuration Options

### Simple Configuration
A single scalar value applies to all operations except pool timeout (which defaults to the same value unless specified) [httpx/_config.py:127-130]().

```python
# 5 second timeout for all operations
timeout = httpx.Timeout(5.0)
```

### Granular Configuration
For precise control, specify individual timeout values [docs/advanced/timeouts.md:65-68]().

```python
# Different timeouts for each operation
timeout = httpx.Timeout(
    connect=10.0,  # 10s to establish connection
    read=30.0,     # 30s to read response
    write=10.0,    # 10s to write request
    pool=5.0       # 5s to get connection from pool
)
```

### Disabling Timeouts
Passing `None` as a timeout value disables the specific timeout [docs/advanced/timeouts.md:23-28]().

```python
# Disable all timeouts
timeout = httpx.Timeout(None)

# 5s default, but no timeout on acquiring from pool
timeout = httpx.Timeout(5.0, pool=None)
```

Sources: [httpx/_config.py:76-84](), [docs/advanced/timeouts.md:19-28](), [docs/advanced/timeouts.md:63-71]()

## Usage Patterns

### Client-Level Configuration
Timeouts can be set on a client instance, serving as the default for all requests [docs/advanced/timeouts.md:32-39]().

```python
client = httpx.Client(timeout=10.0)  # Use a default 10s timeout everywhere
```

### Request-Level Configuration
Individual requests can override client-level settings [docs/advanced/timeouts.md:8-17]().

```python
# Using a client instance with an override
with httpx.Client() as client:
    client.get("http://example.com/", timeout=10.0)
```

### Top-Level API Usage
Convenience functions like `httpx.get()` accept a `timeout` parameter [docs/advanced/timeouts.md:11-12]().

```python
httpx.get('http://example.com/', timeout=10.0)
```

Sources: [docs/advanced/timeouts.md:8-39](), [httpx/_config.py:76-84]()

## Transport Integration

The `Timeout` configuration is passed to the transport layer via request extensions [httpx/_transports/default.py:230-259]().

### Exception Mapping
httpx maps low-level network timeouts to specific exception types [tests/test_timeouts.py:7-56]().

| Exception | Phase | Description |
|-----------|-------|-------------|
| `httpx.ConnectTimeout` | Connection | Socket connection failed within limit [tests/test_timeouts.py:31]() |
| `httpx.ReadTimeout` | Receiving | Data chunk not received within limit [tests/test_timeouts.py:11]() |
| `httpx.WriteTimeout` | Sending | Data chunk not sent within limit [tests/test_timeouts.py:20]() |
| `httpx.PoolTimeout` | Pool | Failed to acquire connection from pool [tests/test_timeouts.py:42]() |

Sources: [tests/test_timeouts.py:7-56](), [docs/advanced/timeouts.md:45-61]()

## Testing and Validation

The `Timeout` class ensures consistency during initialization:
- It requires either a default timeout or explicit values for all four parameters [httpx/_config.py:122-126]().
- It supports tuple-based initialization: `(connect, read, write, pool)` [httpx/_config.py:105-110]().
- It provides an `as_dict()` method for exporting configuration [httpx/_config.py:132-138]().

Sources: [httpx/_config.py:105-138](), [tests/test_config.py:103-162]()

---

# Page: Connection Limits

# Connection Limits

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_config.py](httpx/_config.py)
- [tests/test_api.py](tests/test_api.py)
- [tests/test_config.py](tests/test_config.py)
- [tests/test_timeouts.py](tests/test_timeouts.py)

</details>



This page documents the `httpx.Limits` configuration class, which controls connection pooling behavior in HTTPX clients. Connection limits determine how many concurrent HTTP connections can be established and how long idle connections are kept alive for reuse.

For timeout configuration, see [Timeouts](6.1). For proxy configuration, see [Proxy Support](5.3). For the overall configuration system, see [Configuration](6).

## Overview

The `Limits` class provides three parameters that control connection pooling at the transport layer:

- `max_connections`: Maximum number of concurrent connections.
- `max_keepalive_connections`: Maximum number of idle connections to maintain in the pool.
- `keepalive_expiry`: Time limit (in seconds) before idle connections are closed.

These settings are passed to the underlying `httpcore` library, which manages the actual connection pools.

Sources: [httpx/_config.py:159-199]()

## The Limits Class

The `httpx.Limits` class is a configuration container that holds connection pooling parameters. It is defined in `httpx._config` and is instantiated with keyword arguments.

### Code Entity Relationship

The following diagram illustrates how the `Limits` class interacts with the transport layer and the underlying `httpcore` implementation.

```mermaid
classDiagram
    class Limits {
        +int|None max_connections
        +int|None max_keepalive_connections
        +float|None keepalive_expiry
        +__init__(max_connections, max_keepalive_connections, keepalive_expiry)
        +__eq__(other) bool
        +__repr__() str
    }
    
    class HTTPTransport {
        +ConnectionPool _pool
        +__init__(limits: Limits)
    }
    
    class AsyncHTTPTransport {
        +AsyncConnectionPool _pool
        +__init__(limits: Limits)
    }
    
    class ConnectionPool {
        <<httpcore>>
        +int|None max_connections
        +int|None max_keepalive_connections
        +float|None keepalive_expiry
    }
    
    class AsyncConnectionPool {
        <<httpcore>>
        +int|None max_connections
        +int|None max_keepalive_connections
        +float|None keepalive_expiry
    }
    
    Limits --> HTTPTransport : "configures"
    Limits --> AsyncHTTPTransport : "configures"
    HTTPTransport --> ConnectionPool : "instantiates with limits"
    AsyncHTTPTransport --> AsyncConnectionPool : "instantiates with limits"
```

Sources: [httpx/_config.py:159-199](), [httpx/_transports/default.py:135-216](), [httpx/_transports/default.py:279-359]()

## Configuration Parameters

### max_connections

The `max_connections` parameter controls the maximum number of concurrent TCP connections that may be established to all hosts combined. When this limit is reached, additional requests will wait in a queue until a connection becomes available, eventually triggering a `PoolTimeout` if the wait exceeds the configured pool timeout.

- **Type**: `int | None`
- **Default**: `None` (Note: While `AsyncClient` often defaults to 100 via internal constants, the `Limits` class itself defaults to `None` if not specified).
- **Effect**: Limits total concurrent connections across all hosts.
- **None behavior**: No limit on concurrent connections.

### max_keepalive_connections

The `max_keepalive_connections` parameter controls how many idle connections are retained in the connection pool for reuse. When the pool exceeds this size, the oldest idle connections are closed.

- **Type**: `int | None`
- **Default**: `None`
- **Effect**: Limits how many idle connections are kept alive.
- **None behavior**: No limit on keep-alive connections.
- **Constraint**: Should be less than or equal to `max_connections`.

### keepalive_expiry

The `keepalive_expiry` parameter controls how long (in seconds) an idle connection remains in the pool before being closed automatically.

- **Type**: `float | None`
- **Default**: `5.0` seconds.
- **Effect**: Time limit on idle keep-alive connections.
- **None behavior**: No automatic expiry (connections kept until explicitly closed or dropped by the server).

Sources: [httpx/_config.py:173-182]()

## Usage with Clients

The `Limits` object is typically passed to the `Client` or `AsyncClient` during initialization.

### Limits Configuration Flow

This diagram shows the data flow from user instantiation to the enforcement of limits in the transport layer.

```mermaid
flowchart TD
    User["User Code"] --> |"instantiates"| LimitsObj["httpx.Limits"]
    User --> |"passes to"| Client["httpx.Client / httpx.AsyncClient"]
    
    Client --> |"passes limits to"| Transport["HTTPTransport / AsyncHTTPTransport"]
    
    subgraph TransportLayer ["Transport Layer (httpx/_transports/default.py)"]
        Transport --> |"extracts"| Params["max_connections<br/>max_keepalive_connections<br/>keepalive_expiry"]
        Params --> |"initializes"| CorePool["httpcore.ConnectionPool / AsyncConnectionPool"]
    end
    
    CorePool --> |"enforces"| PoolBehavior["- Queueing requests<br/>- Closing idle connections<br/>- Expiring connections"]
```

Sources: [httpx/_config.py:173-182](), [httpx/_transports/default.py:156-167](), [httpx/_transports/default.py:300-311]()

## Connection Pooling Behavior

### Connection Lifecycle

The following state diagram describes how connections transition between states based on the `Limits` configuration.

```mermaid
stateDiagram-v2
    [*] --> Establishing : "Request initiated"
    Establishing --> Active : "Connection established"
    Active --> Idle : "Request completed"
    Active --> Closed : "Error or server close"
    
    Idle --> Active : "Connection reused"
    Idle --> Closed : "keepalive_expiry reached"
    Idle --> Closed : "Exceeds max_keepalive_connections"
    
    Closed --> [*]
    
    note right of Active
        Limited by max_connections
    end note
    
    note right of Idle
        Limited by max_keepalive_connections
    end note
```

Sources: [httpx/_config.py:165-171](), [tests/test_timeouts.py:37-45]()

### Relationship Between Parameters

The interaction between `max_connections` and `max_keepalive_connections` defines the pooling strategy:

| Configuration | Strategy |
|---------------|----------|
| `max_connections=100, max_keepalive_connections=20` | Standard: High concurrency allowed, moderate reuse pool. |
| `max_connections=50, max_keepalive_connections=50` | Aggressive: Keep every connection alive after use. |
| `max_connections=1, max_keepalive_connections=0` | Serial: No concurrency, no reuse (closes after every request). |

Sources: [httpx/_config.py:165-171]()

## Integration with Proxies

When a proxy is configured, the `Limits` are applied to the proxy connection pool rather than a direct connection pool. The `HTTPTransport` and `AsyncHTTPTransport` classes handle this by passing the `limits` object to `httpcore.HTTPProxy` or `httpcore.SOCKSProxy`.

Sources: [httpx/_transports/default.py:168-186](), [httpx/_transports/default.py:312-330]()

## Testing and Debugging

The `Limits` class implements standard Python protocols for comparison and inspection, which is useful for verifying configuration in test suites.

- `__eq__`: Allows comparing two `Limits` instances to see if they have identical configurations. [httpx/_config.py:184-190]()
- `__repr__`: Provides a string representation of the current limits. [httpx/_config.py:192-198]()

Example from the test suite:
```python
def test_limits_repr():
    limits = httpx.Limits(max_connections=100)
    expected = (
        "Limits(max_connections=100, max_keepalive_connections=None,"
        " keepalive_expiry=5.0)"
    )
    assert repr(limits) == expected
```
Sources: [tests/test_config.py:89-101]()

---

# Page: SSL and Security

# SSL and Security

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [docs/advanced/ssl.md](docs/advanced/ssl.md)
- [docs/environment_variables.md](docs/environment_variables.md)
- [httpx/_config.py](httpx/_config.py)

</details>



This page documents SSL/TLS configuration in `httpx`, including certificate verification, custom SSL contexts, client certificates, and environment variable support. SSL configuration controls how `httpx` validates server certificates and presents client certificates during HTTPS connections.

For information about proxy configuration (which also supports SSL contexts), see [Proxy Support](#5.3). For general client configuration patterns, see [Client API](#3).

## Overview

SSL/TLS security in `httpx` is managed through the `create_ssl_context()` function and configuration parameters passed to clients and transports. The library uses Python's standard `ssl` module and the `certifi` package for default certificate verification.

**Key Configuration Points:**
- **Client instantiation**: `httpx.Client(verify=..., trust_env=...)` [[httpx/_client.py:613-625]]()
- **Top-level functions**: `httpx.get(url, verify=..., trust_env=...)` [[httpx/_api.py:39-44]]()
- **Transport layer**: `HTTPTransport(verify=..., cert=..., trust_env=...)` [[httpx/_transports/default.py:136-149]]()
- **Proxy connections**: `Proxy(url=..., ssl_context=...)` [[httpx/_config.py:202-212]]()

Sources: [httpx/_config.py:23-69](), [httpx/_client.py:613-625](), [httpx/_api.py:39-44]()

## SSL Context Creation

### The create_ssl_context Function

The `create_ssl_context()` function is the central mechanism for SSL context creation in `httpx`. It handles all verification modes and environment variable integration.

Title: SSL Context Creation Logic
```mermaid
graph TB
    Input["create_ssl_context()<br/>verify, cert, trust_env"]
    
    CheckVerify{"verify type?"}
    
    VerifyTrue["verify = True"]
    CheckEnv{"trust_env and<br/>SSL_CERT_FILE set?"}
    UseCertFile["ssl.create_default_context(cafile=SSL_CERT_FILE)"]
    
    CheckEnvDir{"trust_env and<br/>SSL_CERT_DIR set?"}
    UseCertDir["ssl.create_default_context(capath=SSL_CERT_DIR)"]
    
    UseCertifi["ssl.create_default_context(cafile=certifi.where())"]
    
    VerifyFalse["verify = False"]
    CreateUnverified["ssl.SSLContext(PROTOCOL_TLS_CLIENT)<br/>check_hostname=False<br/>verify_mode=CERT_NONE"]
    
    VerifyStr["verify = str"]
    DeprecatedPath["Deprecated:<br/>create_default_context()<br/>with cafile or capath"]
    
    VerifyContext["verify = SSLContext"]
    UseContext["Use provided context"]
    
    CheckCert{"cert parameter<br/>provided?"}
    LoadCert["Deprecated:<br/>ctx.load_cert_chain()"]
    
    Output["SSLContext"]
    
    Input --> CheckVerify
    
    CheckVerify -->|"True"| VerifyTrue
    CheckVerify -->|"False"| VerifyFalse
    CheckVerify -->|"str"| VerifyStr
    CheckVerify -->|"SSLContext"| VerifyContext
    
    VerifyTrue --> CheckEnv
    CheckEnv -->|"yes"| UseCertFile
    CheckEnv -->|"no"| CheckEnvDir
    CheckEnvDir -->|"yes"| UseCertDir
    CheckEnvDir -->|"no"| UseCertifi
    
    VerifyFalse --> CreateUnverified
    VerifyStr --> DeprecatedPath
    VerifyContext --> UseContext
    
    UseCertFile --> CheckCert
    UseCertDir --> CheckCert
    UseCertifi --> CheckCert
    CreateUnverified --> CheckCert
    DeprecatedPath --> CheckCert
    UseContext --> CheckCert
    
    CheckCert -->|"yes"| LoadCert
    CheckCert -->|"no"| Output
    LoadCert --> Output
```

**Function Signature:** [[httpx/_config.py:23-27]]()

**Parameters:**
- `verify`: Controls certificate verification mode (default: `True`) [[httpx/_config.py:24]]()
- `cert`: Deprecated parameter for client certificates (default: `None`) [[httpx/_config.py:25]]()
- `trust_env`: Whether to respect environment variables (default: `True`) [[httpx/_config.py:26]]()

**Return Value:** An `ssl.SSLContext` instance configured according to the parameters [[httpx/_config.py:69]]().

Sources: [httpx/_config.py:23-69]()

## Certificate Verification Modes

### Default Verification (verify=True)

When `verify=True` (the default), `httpx` performs full SSL certificate verification using a trusted certificate authority bundle.

**Priority Order:**
1. `SSL_CERT_FILE` environment variable (if `trust_env=True`) [[httpx/_config.py:34-35]]()
2. `SSL_CERT_DIR` environment variable (if `trust_env=True`) [[httpx/_config.py:36-37]]()
3. Certifi CA bundle (default fallback) [[httpx/_config.py:40]]()

**Implementation:** [[httpx/_config.py:33-40]]()

```python
# Default behavior - uses certifi
response = httpx.get("https://example.com")

# Explicit verification enabled
client = httpx.Client(verify=True)
```

Sources: [httpx/_config.py:33-40](), [docs/advanced/ssl.md:23]()

### Disabling Verification (verify=False)

Setting `verify=False` disables all SSL certificate verification. This should only be used for testing or when connecting to servers with self-signed certificates.

**Security Warning:** Disabling verification makes connections vulnerable to man-in-the-middle attacks.

**Implementation:** [[httpx/_config.py:41-44]]()

```python
# Disable verification (insecure)
response = httpx.get("https://expired.badssl.com/", verify=False)

# Client with verification disabled
client = httpx.Client(verify=False)
```

**Unverified Context Properties:**
| Property | Value | Code Pointer |
|----------|-------|--------------|
| Protocol | `ssl.PROTOCOL_TLS_CLIENT` | [[httpx/_config.py:42]]() |
| `check_hostname` | `False` | [[httpx/_config.py:43]]() |
| `verify_mode` | `ssl.CERT_NONE` | [[httpx/_config.py:44]]() |

Sources: [httpx/_config.py:41-44](), [docs/advanced/ssl.md:12-17]()

### Custom SSL Context (verify=SSLContext)

For advanced SSL configuration, pass a custom `ssl.SSLContext` instance. This provides full control over SSL/TLS settings.

```python
import ssl
import certifi
import httpx

# Custom SSL context with specific settings
ctx = ssl.create_default_context(cafile=certifi.where())
client = httpx.Client(verify=ctx)
```

**Use Cases:**
- Loading alternative CA bundles [[docs/advanced/ssl.md:52-58]]()
- Using system certificate stores via the `truststore` package [[docs/advanced/ssl.md:37-47]]()

Sources: [httpx/_config.py:55-56](), [docs/advanced/ssl.md:25-58]()

### Deprecated String Path (verify=str)

Passing a string path to `verify` is deprecated. It will be removed in a future version. Users should use `ssl.create_default_context(cafile=...)` instead [[httpx/_config.py:45-51]]().

**Implementation:** [[httpx/_config.py:52-54]]()

Sources: [httpx/_config.py:45-54]()

## Environment Variables

`httpx` respects standard SSL environment variables when `trust_env=True` (the default) [[docs/environment_variables.md:3-9]]().

### SSL_CERT_FILE

Specifies the path to a single CA certificate file in PEM format [[docs/environment_variables.md:55-61]]().

**Implementation:** [[httpx/_config.py:34-35]]()

### SSL_CERT_DIR

Specifies the path to a directory containing CA certificates in OpenSSL's hashed directory format [[docs/environment_variables.md:69-73]]().

**Implementation:** [[httpx/_config.py:36-37]]()

Sources: [httpx/_config.py:34-37](), [docs/environment_variables.md:55-79]()

## Client Certificates

Client certificates (mutual TLS) allow servers to authenticate the client.

### Loading Client Certificates

Client certificates should be loaded onto an `ssl.SSLContext` using the `.load_cert_chain()` method [[docs/advanced/ssl.md:60-70]]().

```python
import ssl
import httpx

ctx = ssl.create_default_context()
ctx.load_cert_chain(certfile="path/to/client.pem")
client = httpx.Client(verify=ctx)
```

Sources: [docs/advanced/ssl.md:60-70]()

### Deprecated cert Parameter

The `cert` parameter on `Client` and `create_ssl_context()` is deprecated [[httpx/_config.py:58-63]]().

**CertTypes Definition:** [[httpx/_types.py:60]]()
```python
CertTypes = Union[str, Tuple[str, str], Tuple[str, str, str]]
```

Sources: [httpx/_config.py:58-67](), [httpx/_types.py:60]()

## SSL in the Transport Layer

The transport layer is where SSL contexts are applied to network connections.

Title: Bridge between Client Configuration and Transport Implementation
```mermaid
graph LR
    subgraph "Client Layer"
        C["httpx.Client"]
        AC["httpx.AsyncClient"]
    end
    
    subgraph "Configuration Layer"
        CSC["create_ssl_context()"]
    end
    
    subgraph "Transport Layer"
        HT["HTTPTransport"]
        AHT["AsyncHTTPTransport"]
    end
    
    subgraph "Core Layer"
        HCP["httpcore.ConnectionPool"]
    end
    
    C -->|"uses"| HT
    AC -->|"uses"| AHT
    HT -->|"calls"| CSC
    AHT -->|"calls"| CSC
    CSC -->|"returns ssl.SSLContext"| HT
    HT -->|"passes ssl_context to"| HCP
```

**Implementation:**
- `HTTPTransport` creates the context in `__init__` [[httpx/_transports/default.py:153]]().
- `AsyncHTTPTransport` creates the context in `__init__` [[httpx/_transports/default.py:297]]().

Sources: [httpx/_transports/default.py:136-153](), [httpx/_transports/default.py:280-297]()

## Proxy SSL Contexts

The `Proxy` class supports a separate `ssl_context` for the connection to the proxy server itself [[httpx/_config.py:202-212]]().

Title: SSL Context Separation for Proxies
```mermaid
graph TB
    subgraph "Client Configuration"
        TargetSSL["Target SSL Context<br/>(via verify=...)"]
    end
    
    subgraph "Proxy Configuration"
        ProxyObj["httpx.Proxy"]
        ProxySSL["Proxy SSL Context<br/>(via ssl_context=...)"]
    end
    
    subgraph "Network Flow"
        Client["httpx.Client"]
        ProxyServer["Proxy Server"]
        TargetServer["Target Server"]
    end
    
    ProxyObj -->|"holds"| ProxySSL
    Client -->|"uses"| ProxyObj
    Client -->|"Connects via ProxySSL"| ProxyServer
    Client -->|"Tunnel via TargetSSL"| TargetServer
```

**Implementation:** The proxy's SSL context is passed to `httpcore` as `proxy_ssl_context` [[httpx/_transports/default.py:179]]().

Sources: [httpx/_config.py:202-212](), [httpx/_transports/default.py:168-186]()

## Summary Table

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `verify` | `Union[SSLContext, str, bool]` | `True` | SSL verification settings [[httpx/_config.py:24]]() |
| `cert` | `CertTypes` | `None` | Deprecated client certificate [[httpx/_config.py:25]]() |
| `trust_env` | `bool` | `True` | Respect environment variables [[httpx/_config.py:26]]() |

Sources: [httpx/_config.py:23-69]()

---

# Page: Event Hooks

# Event Hooks

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [docs/advanced/authentication.md](docs/advanced/authentication.md)
- [docs/advanced/event-hooks.md](docs/advanced/event-hooks.md)
- [docs/advanced/resource-limits.md](docs/advanced/resource-limits.md)
- [docs/advanced/text-encodings.md](docs/advanced/text-encodings.md)
- [docs/advanced/timeouts.md](docs/advanced/timeouts.md)
- [tests/client/test_event_hooks.py](tests/client/test_event_hooks.py)

</details>



Event hooks provide a middleware-like mechanism for monitoring and intercepting requests and responses during the HTTP request lifecycle. They allow custom callback functions to be executed at specific points: after a request is fully prepared but before it is sent, and after a response is received from the network but before it is returned to the caller.

Event hooks are particularly useful for cross-cutting concerns such as logging, metrics collection, debugging, and automated response processing (e.g., raising exceptions on error status codes).

## Overview

Event hooks in `httpx` are defined as lists of callable objects. The client maintains two distinct hook types:

- **`request`**: Called after a request is fully prepared, but before it is sent to the network. Passed the `request` instance. [docs/advanced/event-hooks.md:6-6]()
- **`response`**: Called after the response has been fetched from the network, but before it is returned to the caller. Passed the `response` instance. [docs/advanced/event-hooks.md:7-7]()

These hooks are allowed to modify the `request` and `response` objects in-place. [docs/advanced/event-hooks.md:40-40]()

Sources: [docs/advanced/event-hooks.md:1-9](), [tests/client/test_event_hooks.py:19-25]()

## Hook Registration

### Client-Level Registration

Event hooks are registered when creating a `Client` or `AsyncClient` instance through the `event_hooks` parameter. The parameter expects a dictionary mapping hook names to **lists** of callables. [docs/advanced/event-hooks.md:49-50]()

```python
def log_request(request):
    print(f"Request: {request.method} {request.url}")

def log_response(response):
    print(f"Response: {response.status_code}")

client = httpx.Client(
    event_hooks={
        "request": [log_request],
        "response": [log_response],
    }
)
```
Sources: [docs/advanced/event-hooks.md:11-20](), [tests/client/test_event_hooks.py:25-29]()

### Async Hook Requirements

If using `httpx.AsyncClient`, hooks registered **MUST** be `async` functions. Conversely, `httpx.Client` uses standard synchronous functions. [docs/advanced/event-hooks.md:62-66]()

```python
async def async_log_request(request):
    await do_async_logging(request)

client = httpx.AsyncClient(event_hooks={'request': [async_log_request]})
```
Sources: [docs/advanced/event-hooks.md:62-66](), [tests/client/test_event_hooks.py:70-76]()

### Modifying Hooks at Runtime

The client instance exposes an `.event_hooks` property that allows inspection and modification of installed hooks after instantiation. [docs/advanced/event-hooks.md:52-55]()

```python
client = httpx.Client()
client.event_hooks['request'] = [log_request]
client.event_hooks['response'].append(raise_on_4xx_5xx)
```
Sources: [docs/advanced/event-hooks.md:56-60]()

## Event Hook Execution Flow

The following diagram illustrates the integration of hooks within the request-response cycle, including how they interact with redirects.

```mermaid
flowchart TD
    subgraph "Request Preparation"
        A["Client.build_request()"] --> B["Finalize Request Object"]
    end

    subgraph "Hook Execution (Request)"
        B --> C["Execute 'request' hooks"]
    end

    subgraph "Network I/O"
        C --> D["Transport.handle_request()"]
        D --> E["Receive Response Headers"]
    end

    subgraph "Hook Execution (Response)"
        E --> F["Execute 'response' hooks"]
    end

    subgraph "Post-Processing"
        F --> G{"Follow Redirect?"}
        G -- "Yes" --> A
        G -- "No" --> H["Return Response to User"]
    end

    classDef hook fill:#f9f9f9,stroke-dasharray: 5 5
    class C,F hook
```
**Event Hook Lifecycle**

When `follow_redirects=True` is enabled, a redirect triggers additional "request" and "response" event hooks for every step in the redirect chain. [tests/client/test_event_hooks.py:118-121]()

Sources: [docs/advanced/event-hooks.md:6-7](), [tests/client/test_event_hooks.py:133-138](), [tests/client/test_event_hooks.py:140-171]()

## Implementation Details

### Data Flow and Entities

The following diagram maps the natural language concepts of "Hooks" to the specific classes and methods used in the `httpx` codebase.

```mermaid
classDiagram
    class Client {
        +event_hooks: dict
        +get(url)
        +post(url)
    }
    class AsyncClient {
        +event_hooks: dict
        +get(url)
    }
    class Request {
        +method: str
        +url: URL
        +headers: Headers
    }
    class Response {
        +status_code: int
        +request: Request
        +raise_for_status()
    }

    Client "1" *-- "many" Request : builds
    Client "1" *-- "many" Response : receives
    Client --> Request : "calls 'request' hooks with"
    Client --> Response : "calls 'response' hooks with"
    AsyncClient --> Request : "awaits 'request' hooks with"
    AsyncClient --> Response : "awaits 'response' hooks with"
```
**Entity Association Diagram**

Sources: [docs/advanced/event-hooks.md:11-20](), [tests/client/test_event_hooks.py:19-23](), [tests/client/test_event_hooks.py:70-74]()

### Response Body Access

Response event hooks are called **before** the client determines if the response body should be read. If a hook needs to inspect the body (e.g., for logging JSON error payloads), it must explicitly trigger the read. [docs/advanced/event-hooks.md:33-35]()

- In `Client` hooks: Call `response.read()`. [docs/advanced/event-hooks.md:37-38]()
- In `AsyncClient` hooks: Call `await response.aread()`. [docs/advanced/event-hooks.md:38-38]()

## Common Patterns

### Automated Error Handling
A common pattern is to use a response hook to automatically call `.raise_for_status()` on all responses, ensuring that 4xx and 5xx responses always raise an `httpx.HTTPStatusError`. [docs/advanced/event-hooks.md:22-25]()

```python
def raise_on_4xx_5xx(response):
    response.raise_for_status()

client = httpx.Client(event_hooks={'response': [raise_on_4xx_5xx]})
```
When an exception is raised inside a response hook, the response is automatically closed. [tests/client/test_event_hooks.py:62-63]()

Sources: [docs/advanced/event-hooks.md:27-31](), [tests/client/test_event_hooks.py:52-63]()

### Request Augmentation
Hooks can be used to add headers to every request, such as timestamps or tracing IDs, after the request has been fully prepared by the client logic. [docs/advanced/event-hooks.md:40-41]()

```python
def add_timestamp(request):
    request.headers['x-request-timestamp'] = datetime.now(tz=datetime.utc).isoformat()

client = httpx.Client(event_hooks={'request': [add_timestamp]})
```
Sources: [docs/advanced/event-hooks.md:43-47]()

## Comparison with Authentication Flows

While both Event Hooks and `httpx.Auth` subclasses can intercept requests, they serve different purposes:

| Feature | Event Hooks | Auth Flow (`httpx.Auth`) |
| :--- | :--- | :--- |
| **Primary Purpose** | Logging, monitoring, global processing | Credentials, challenge-response negotiation |
| **Mechanism** | Simple callback (Callable) | Generator-based flow (`yield`) |
| **I/O Support** | Sync in Client, Async in AsyncClient | Designed to be I/O agnostic (works in both) |
| **Body Access** | Requires manual `.read()`/`.aread()` | Uses `requires_request_body` property |

Sources: [docs/advanced/event-hooks.md:1-9](), [docs/advanced/authentication.md:94-125]()

---

# Page: Command Line Interface

# Command Line Interface

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_main.py](httpx/_main.py)
- [pyproject.toml](pyproject.toml)
- [requirements.txt](requirements.txt)
- [tests/test_main.py](tests/test_main.py)

</details>



The `httpx` command line interface provides a complete HTTP client tool for making requests from the terminal. This tool is available when `httpx` is installed with the `[cli]` extra, which pulls in dependencies like `click`, `pygments`, and `rich`. The CLI functionality is primarily implemented in the `httpx/_main.py` module.

For information about the underlying Client API used by the CLI, see [Client API](#3). For details about authentication mechanisms, see [Authentication](#2.3).

## CLI Entry Point and Architecture

The httpx CLI is built using the `click` library and provides a rich terminal experience with syntax highlighting and progress indicators. The main entry point is defined by the `main()` function, which serves as the CLI command handler.

### System Mapping: CLI to Code Entities

The following diagram maps high-level CLI concepts to their specific implementations within `httpx/_main.py`.

```mermaid
graph TB
    subgraph "CLI Entry Points"
        CliCommand["main() in httpx/_main.py"]
        HelpHandler["handle_help() in httpx/_main.py"]
        PrintHelp["print_help() in httpx/_main.py"]
    end
    
    subgraph "Input Processing"
        UrlArg["URL argument"]
        MethodOption["--method / -m"]
        ParamsOption["--params / -p"]
        DataOptions["--data / -d, --json / -j, --files / -f"]
        AuthOption["--auth"]
        ConfigOptions["--timeout, --proxy, --http2"]
    end
    
    subgraph "Validation Layer"
        ValidateJson["validate_json() in httpx/_main.py"]
        ValidateAuth["validate_auth() in httpx/_main.py"]
    end
    
    subgraph "Request Execution"
        ClientCreation["httpx.Client instantiation"]
        StreamRequest["client.stream() call"]
        TraceExtension["trace() callback function"]
    end
    
    subgraph "Response Processing"
        ResponseHandling["httpx.Response object"]
        PrintResponse["print_response() in httpx/_main.py"]
        DownloadResponse["download_response() in httpx/_main.py"]
        FormatHeaders["print_request_headers() / print_response_headers()"]
    end
    
    CliCommand --> UrlArg
    CliCommand --> MethodOption
    CliCommand --> ParamsOption
    CliCommand --> DataOptions
    CliCommand --> AuthOption
    CliCommand --> ConfigOptions
    
    DataOptions --> ValidateJson
    AuthOption --> ValidateAuth
    
    CliCommand --> ClientCreation
    ClientCreation --> StreamRequest
    StreamRequest --> TraceExtension
    
    StreamRequest --> ResponseHandling
    ResponseHandling --> PrintResponse
    ResponseHandling --> DownloadResponse
    TraceExtension --> FormatHeaders
    
    HelpHandler --> PrintHelp
```

Sources: [httpx/_main.py:313-451](), [httpx/_main.py:452-506](), [pyproject.toml:43-47](), [pyproject.toml:58-59]()

## Command Structure and Options

The CLI accepts a URL as the primary argument and supports numerous options for configuring requests. The command structure follows the pattern:

```bash
httpx <URL> [OPTIONS]
```

### Core Request Options

| Option | Short | Type | Description |
|--------|-------|------|-------------|
| `--method` | `-m` | str | HTTP method (GET, POST, PUT, etc.) [httpx/_main.py:322-326]() |
| `--params` | `-p` | tuple | Query parameters as name-value pairs [httpx/_main.py:327-330]() |
| `--content` | `-c` | str | Raw byte content for request body [httpx/_main.py:331-333]() |
| `--data` | `-d` | tuple | Form data as name-value pairs [httpx/_main.py:334-337]() |
| `--files` | `-f` | tuple | Files for multipart upload [httpx/_main.py:338-341]() |
| `--json` | `-j` | str | JSON data for request body [httpx/_main.py:342-345]() |
| `--headers` | `-h` | tuple | Additional HTTP headers [httpx/_main.py:346-349]() |
| `--cookies` | | tuple | Cookies to include [httpx/_main.py:350-353]() |
| `--auth` | | tuple | Username/password authentication [httpx/_main.py:354-358]() |

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--proxy` | str | None | Proxy URL [httpx/_main.py:365-368]() |
| `--timeout` | float | 5.0 | Network timeout in seconds [httpx/_main.py:369-373]() |
| `--follow-redirects` | flag | False | Automatically follow redirects [httpx/_main.py:374-375]() |
| `--no-verify` | flag | True | Disable SSL verification [httpx/_main.py:376-377]() |
| `--http2` | flag | False | Use HTTP/2 if supported [httpx/_main.py:378-380]() |
| `--verbose` | `-v` | flag | Show request headers and connection details [httpx/_main.py:386-388]() |
| `--download` | file | None | Save response to file [httpx/_main.py:381-385]() |

Sources: [httpx/_main.py:315-451]()

## Request Processing Pipeline

The CLI processes requests through a structured pipeline that validates inputs, creates a `Client` instance, and executes the request.

```mermaid
graph LR
    subgraph "Input Validation"
        ClickParsing["Click option parsing"]
        JsonValidation["validate_json()"]
        AuthValidation["validate_auth()"]
    end
    
    subgraph "Method Selection"
        MethodLogic["Method determination logic"]
        DefaultGet["Default: GET"]
        DefaultPost["POST if body content"]
    end
    
    subgraph "Client Configuration"
        ClientInit["Client(proxy, timeout, http2, verify)"]
        StreamCall["client.stream()"]
        ExtensionsConfig["extensions={'trace': trace}"]
    end
    
    subgraph "Request Parameters"
        ParamsDict["dict(params)"]
        DataDict["dict(data)"] 
        HeadersList["headers list"]
        CookiesDict["dict(cookies)"]
        FilesHandling["files handling"]
    end
    
    ClickParsing --> JsonValidation
    ClickParsing --> AuthValidation
    
    JsonValidation --> MethodLogic
    AuthValidation --> MethodLogic
    
    MethodLogic --> DefaultGet
    MethodLogic --> DefaultPost
    
    DefaultGet --> ClientInit
    DefaultPost --> ClientInit
    
    ClientInit --> StreamCall
    StreamCall --> ExtensionsConfig
    
    ParamsDict --> StreamCall
    DataDict --> StreamCall
    HeadersList --> StreamCall
    CookiesDict --> StreamCall
    FilesHandling --> StreamCall
```

The logic for determining the HTTP method defaults to `GET`, but switches to `POST` if `content`, `data`, `files`, or `json` parameters are provided [httpx/_main.py:464-467]().

Sources: [httpx/_main.py:452-506](), [httpx/_main.py:287-299](), [httpx/_main.py:273-285]()

## Response Handling and Formatting

The CLI provides sophisticated response handling with syntax highlighting, content detection, and multiple output formats.

### Response Display Logic

The CLI uses `print_response()` to display content to the terminal. It attempts to detect the appropriate `pygments` lexer via `get_lexer_for_response()` by inspecting the `Content-Type` header [httpx/_main.py:103-114](). If the content is identified as JSON, it is pretty-printed using `json.dumps(indent=4)` [httpx/_main.py:174-177]().

```mermaid
graph TD
    subgraph "Response Processing"
        ResponseObj["httpx.Response object"]
        DownloadCheck["--download parameter?"]
        ContentCheck["Binary vs Text check"]
    end
    
    subgraph "Download Path"
        DownloadFunc["download_response()"]
        ProgressBar["rich.progress.Progress"]
        FileWrite["Write to disk"]
    end
    
    subgraph "Display Path"
        PrintFunc["print_response()"]
        LexerDetection["get_lexer_for_response()"]
        ContentTypeCheck["Content-Type header analysis"]
    end
    
    subgraph "Content Formatting"
        JsonFormatting["JSON pretty printing"]
        SyntaxHighlight["rich.syntax.Syntax highlighting"]
        BinaryDisplay["'binary data' placeholder"]
    end
    
    ResponseObj --> DownloadCheck
    ResponseObj --> ContentCheck
    
    DownloadCheck --> DownloadFunc
    DownloadFunc --> ProgressBar
    ProgressBar --> FileWrite
    
    ContentCheck --> PrintFunc
    PrintFunc --> LexerDetection
    LexerDetection --> ContentTypeCheck
    
    ContentTypeCheck --> JsonFormatting
    ContentTypeCheck --> SyntaxHighlight
    ContentTypeCheck --> BinaryDisplay
```

Sources: [httpx/_main.py:494-500](), [httpx/_main.py:170-187](), [httpx/_main.py:103-114](), [httpx/_main.py:251-271]()

## Verbose Output and Tracing

The `--verbose` flag enables detailed tracing of the HTTP request process, showing connection details, TLS information, and request/response headers. This is implemented by passing a `trace` callback to the `extensions` dictionary of the request [httpx/_main.py:488]().

### Trace Event Handling

The `trace()` function handles various `httpcore` trace events to provide detailed connection and protocol information:

| Event Name | Action |
|------------|--------|
| `connection.connect_tcp.started` | Print "Connecting to..." [httpx/_main.py:214-215]() |
| `connection.connect_tcp.complete` | Print "Connected to..." [httpx/_main.py:216-217]() |
| `connection.start_tls.complete` | Print TLS version, cipher, and certificate details [httpx/_main.py:223-234]() |
| `http11.send_request_headers.started` | Print formatted HTTP/1.1 request headers [httpx/_main.py:235-237]() |
| `http2.send_request_headers.started` | Print formatted HTTP/2 request headers [httpx/_main.py:238-240]() |
| `http11.receive_response_headers.complete` | Print formatted HTTP/1.1 response headers [httpx/_main.py:241-244]() |
| `http2.receive_response_headers.complete` | Print formatted HTTP/2 response headers [httpx/_main.py:245-248]() |

Sources: [httpx/_main.py:212-249](), [httpx/_main.py:116-127](), [httpx/_main.py:129-145]()

## Authentication and Security Features

The CLI supports HTTP Basic Authentication through the `--auth` option. If the password is provided as `-`, the CLI uses `click.prompt` to securely ask for the password [httpx/_main.py:291-294]().

### Security Warning
Using `--verbose` or `-v` with authentication will expose the `Authorization` header in the terminal output, which includes the password encoding in a trivially reversible format (Base64) [httpx/_main.py:356-358]().

Sources: [httpx/_main.py:287-299](), [httpx/_main.py:354-358]()

## Error Handling and Exit Codes

The CLI implements error handling to provide clean output for common network failures.

*   **Exit Code 0**: Successful request (including 4xx/5xx responses, unless they cause an exception) [httpx/_main.py:506]().
*   **Exit Code 1**: Network errors, connection timeouts, or invalid parameters. The CLI catches `httpx.RequestError` and prints the error class and message [httpx/_main.py:501-505]().

Sources: [httpx/_main.py:501-506](), [tests/test_main.py:181-188]()

## Rich Terminal Integration

The CLI extensively uses the `Rich` library for enhanced terminal output:

| Component | Purpose | Implementation |
|-----------|---------|----------------|
| `rich.console.Console` | Main output interface | [httpx/_main.py:27]() |
| `rich.syntax.Syntax` | Code syntax highlighting | [httpx/_main.py:150](), [httpx/_main.py:183]() |
| `rich.progress.Progress` | Download progress bars | [httpx/_main.py:255]() |
| `rich.table.Table` | Help formatting | [httpx/_main.py:38]() |

Sources: [httpx/_main.py:26-36](), [httpx/_main.py:251-271](), [httpx/_main.py:170-187]()

---

# Page: Error Handling

# Error Handling

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/__init__.py](httpx/__init__.py)
- [httpx/_exceptions.py](httpx/_exceptions.py)
- [tests/test_exceptions.py](tests/test_exceptions.py)

</details>



This page provides a comprehensive guide to the exception system in HTTPX. It covers the exception hierarchy, how network failures are categorized, and strategies for handling different failure modes in both synchronous and asynchronous contexts.

For information about making requests, see [Basic Usage](#2), and for details about response processing, see [Working with Responses](#2.2).

## Exception Hierarchy

HTTPX implements a structured exception hierarchy in `httpx/_exceptions.py`. This organization enables developers to handle errors at various levels of specificity, from catching all HTTP-related errors to handling very specific network conditions.

The base of the hierarchy is `HTTPError` [httpx/_exceptions.py:74-90](), which is the parent for both `RequestError` (transport/network issues) and `HTTPStatusError` (bad response codes).

### Exception Tree Overview

```mermaid
graph TD
    subgraph "Base Hierarchy"
        HTTPError["HTTPError"] --> RequestError["RequestError"]
        HTTPError --> HTTPStatusError["HTTPStatusError"]
    end
    
    subgraph "Request & Transport Failures"
        RequestError --> TransportError["TransportError"]
        RequestError --> DecodingError["DecodingError"]
        RequestError --> TooManyRedirects["TooManyRedirects"]
    end
    
    subgraph "Network & Timeouts"
        TransportError --> TimeoutException["TimeoutException"]
        TransportError --> NetworkError["NetworkError"]
        TransportError --> ProtocolError["ProtocolError"]
        TransportError --> ProxyError["ProxyError"]
    end

    subgraph "Specific Timeouts"
        TimeoutException --> ConnectTimeout["ConnectTimeout"]
        TimeoutException --> ReadTimeout["ReadTimeout"]
        TimeoutException --> WriteTimeout["WriteTimeout"]
        TimeoutException --> PoolTimeout["PoolTimeout"]
    end

    subgraph "Specific Network Errors"
        NetworkError --> ConnectError["ConnectError"]
        NetworkError --> ReadError["ReadError"]
        NetworkError --> WriteError["WriteError"]
    end
```

Sources: [httpx/_exceptions.py:1-32](), [httpx/_exceptions.py:43-71]()

## Key Exception Categories

### 1. Exception Hierarchy
The hierarchy separates operational errors (like network timeouts) from protocol errors and status code errors. Most exceptions that occur during a request lifecycle will inherit from `RequestError` [httpx/_exceptions.py:107-111]().

For details, see [Exception Hierarchy](#7.1).

### 2. Handling Network Errors
Network-level failures are encapsulated under `TransportError` [httpx/_exceptions.py:123-126](). These include:
* **Timeouts**: `ConnectTimeout`, `ReadTimeout`, `WriteTimeout`, and `PoolTimeout` [httpx/_exceptions.py:132-162]().
* **Connectivity**: `ConnectError`, `ReadError`, and `WriteError` [httpx/_exceptions.py:167-198]().

HTTPX automatically maps low-level exceptions from the underlying `httpcore` library into these high-level HTTPX exceptions [tests/test_exceptions.py:14-37]().

For details, see [Handling Network Errors](#7.2).

### 3. HTTP Status Errors
Unlike some clients, HTTPX does not raise an exception on 4xx or 5xx responses by default. To trigger an exception for unsuccessful status codes, you must call `response.raise_for_status()`. This raises an `HTTPStatusError` [httpx/_exceptions.py:258-269]().

For details, see [HTTP Status Errors](#7.3).

## The Request Property

A significant feature of HTTPX exceptions is the ability to access the `Request` object that caused the error. Both `HTTPError` and `RequestError` include a `.request` property [httpx/_exceptions.py:97-105]().

```python
try:
    response = httpx.get("https://example.com/api")
    response.raise_for_status()
except httpx.HTTPError as exc:
    # Access the request object that failed
    print(f"Error during {exc.request.method} to {exc.request.url}")
```

In the case of `HTTPStatusError`, you also have access to the `.response` property [httpx/_exceptions.py:265-268]().

Sources: [httpx/_exceptions.py:92-105](), [httpx/_exceptions.py:265-268]()

## Code-to-Entity Mapping

The following diagram bridges the natural language concepts of "Network Failures" to the specific classes used in the `httpx` codebase.

```mermaid
graph LR
    subgraph "Natural Language Space"
        CN["Connection Refused"]
        TO["Server taking too long"]
        PR["Malformed HTTP Response"]
    end

    subgraph "Code Entity Space (httpx._exceptions)"
        CN --> ConnectError["ConnectError"]
        TO --> ReadTimeout["ReadTimeout"]
        PR --> RemoteProtocolError["RemoteProtocolError"]
    end

    subgraph "Underlying Layer (httpcore)"
        ConnectError -.-> HC_CE["httpcore.ConnectError"]
        ReadTimeout -.-> HC_RT["httpcore.ReadTimeout"]
    end
```

Sources: [httpx/_exceptions.py:146-150](), [httpx/_exceptions.py:187-191](), [httpx/_exceptions.py:232-238](), [tests/test_exceptions.py:39-52]()

## Common Error Handling Patterns

### Catching All Request Failures
To catch any issue that prevented a successful response (network issues, timeouts, redirects), catch `httpx.RequestError` [httpx/_exceptions.py:107-111]().

### Handling Specific Timeouts
If you need to differentiate between a slow connection and a slow data transfer:
```python
try:
    client.get("...")
except httpx.ConnectTimeout:
    ... # Handle connection issue
except httpx.ReadTimeout:
    ... # Handle slow response issue
```

### Programming Errors
Some exceptions indicate developer errors rather than runtime environmental issues. These inherit from `StreamError` [httpx/_exceptions.py:297-307]() or `RuntimeError`:
* `StreamConsumed`: Attempting to read a response body that has already been read [httpx/_exceptions.py:309]().
* `ResponseNotRead`: Attempting to access `.content` on a streaming response before calling `.read()` [httpx/_exceptions.py:321]().

Sources: [httpx/_exceptions.py:291-321](), [httpx/__init__.py:43-100]()

---

# Page: Exception Hierarchy

# Exception Hierarchy

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [docs/advanced/extensions.md](docs/advanced/extensions.md)
- [docs/exceptions.md](docs/exceptions.md)
- [docs/img/speakeasy.png](docs/img/speakeasy.png)
- [docs/overrides/partials/nav.html](docs/overrides/partials/nav.html)
- [httpx/__init__.py](httpx/__init__.py)
- [httpx/_exceptions.py](httpx/_exceptions.py)
- [mkdocs.yml](mkdocs.yml)
- [tests/test_exceptions.py](tests/test_exceptions.py)

</details>



This page documents the exception hierarchy in HTTPX, providing a comprehensive overview of all exception types that can be raised during HTTP operations. For information about handling specific network-related errors, see [Handling Network Errors](#7.2), and for handling HTTP status code errors, see [HTTP Status Errors](#7.3).

## Overview

HTTPX implements a well-structured exception hierarchy that allows developers to catch specific types of errors or broad categories as needed. The library maps lower-level `httpcore` exceptions to its own internal hierarchy to provide a consistent API for users.

### The Exception Class Tree

```mermaid
graph TD
    HTTPError["HTTPError (Base exception)"]
    
    HTTPError --> RequestError["RequestError"]
    HTTPError --> HTTPStatusError["HTTPStatusError"]
    
    RequestError --> TransportError["TransportError"]
    RequestError --> DecodingError["DecodingError"]
    RequestError --> TooManyRedirects["TooManyRedirects"]
    
    TransportError --> TimeoutException["TimeoutException"]
    TransportError --> NetworkError["NetworkError"]
    TransportError --> ProtocolError["ProtocolError"]
    TransportError --> ProxyError["ProxyError"]
    TransportError --> UnsupportedProtocol["UnsupportedProtocol"]
    
    TimeoutException --> ConnectTimeout["ConnectTimeout"]
    TimeoutException --> ReadTimeout["ReadTimeout"]
    TimeoutException --> WriteTimeout["WriteTimeout"]
    TimeoutException --> PoolTimeout["PoolTimeout"]
    
    NetworkError --> ConnectError["ConnectError"]
    NetworkError --> ReadError["ReadError"]
    NetworkError --> WriteError["WriteError"]
    NetworkError --> CloseError["CloseError"]
    
    ProtocolError --> LocalProtocolError["LocalProtocolError"]
    ProtocolError --> RemoteProtocolError["RemoteProtocolError"]
    
    InvalidURL["InvalidURL"]
    CookieConflict["CookieConflict"]
    
    StreamError["StreamError"]
    StreamError --> StreamConsumed["StreamConsumed"]
    StreamError --> StreamClosed["StreamClosed"]
    StreamError --> ResponseNotRead["ResponseNotRead"]
    StreamError --> RequestNotRead["RequestNotRead"]
```

Sources: [httpx/_exceptions.py:1-32](), [httpx/_exceptions.py:74-363]()

## Major Exception Categories

The HTTPX exception system is divided into three main categories:

1.  **HTTP Errors** - The `HTTPError` branch for errors during HTTP requests and responses.
2.  **Independent Exceptions** - `InvalidURL` and `CookieConflict` for specialized error conditions.
3.  **Stream Errors** - The `StreamError` branch for issues with request and response streams.

### HTTPError Branch

`HTTPError` is the base class for all HTTP-related exceptions in HTTPX [httpx/_exceptions.py:74-76](). It serves as the parent class for two major exception types:

1.  `RequestError`: For errors that occur during the request process, such as network failures or timeouts [httpx/_exceptions.py:107-110]().
2.  `HTTPStatusError`: For HTTP responses with error status codes (4xx or 5xx) [httpx/_exceptions.py:258-263]().

All `HTTPError` instances have a `.request` property that provides access to the original `httpx.Request` instance that caused the error [httpx/_exceptions.py:97-100]().

Sources: [httpx/_exceptions.py:74-105]()

#### HTTPError Request Context

When an exception is raised within a client, HTTPX uses a `request_context` context manager to ensure the `Request` object is attached to the exception before it propagates to the user.

```mermaid
sequenceDiagram
    participant User as "User Code"
    participant Client as "httpx.Client"
    participant Context as "request_context (Manager)"
    participant Transport as "BaseTransport"
    
    User->>Client: get(url)
    Client->>Context: enter context
    Client->>Transport: handle_request(request)
    
    alt Network Failure
        Transport-->>Client: raise ConnectError
        Client->>Context: exit context
        Context->>Context: set exception.request = request
        Context-->>User: propagate ConnectError
    else Status Code Error
        Transport-->>Client: Response
        Client-->>User: Response
        User->>User: response.raise_for_status()
        Note over User: raise HTTPStatusError
    end
```

Sources: [httpx/_exceptions.py:112-120](), [httpx/_exceptions.py:366-379]()

## Request Errors

`RequestError` is the base class for all exceptions that may occur when issuing a `.request()` [httpx/_exceptions.py:107-110]().

### Transport Errors

`TransportError` is the parent class for all exceptions occurring at the level of the Transport API [httpx/_exceptions.py:123-126]().

#### Timeout Exceptions

These exceptions inherit from `TimeoutException` [httpx/_exceptions.py:132-138]().

| Exception Class | Description |
| :--- | :--- |
| `ConnectTimeout` | Timed out while connecting to the host [httpx/_exceptions.py:140-144](). |
| `ReadTimeout` | Timed out while receiving data from the host [httpx/_exceptions.py:146-150](). |
| `WriteTimeout` | Timed out while sending data to the host [httpx/_exceptions.py:152-156](). |
| `PoolTimeout` | Timed out waiting to acquire a connection from the pool [httpx/_exceptions.py:158-162](). |

Sources: [httpx/_exceptions.py:132-161]()

#### Network Errors

These exceptions inherit from `NetworkError` [httpx/_exceptions.py:167-173]().

| Exception Class | Description |
| :--- | :--- |
| `ConnectError` | Failed to establish a connection [httpx/_exceptions.py:187-191](). |
| `ReadError` | Failed to receive data from the network [httpx/_exceptions.py:175-179](). |
| `WriteError` | Failed to send data through the network [httpx/_exceptions.py:181-185](). |
| `CloseError` | Failed to close a connection [httpx/_exceptions.py:193-197](). |

Sources: [httpx/_exceptions.py:167-196]()

#### Protocol Errors

These exceptions inherit from `ProtocolError` [httpx/_exceptions.py:216-220]().

| Exception Class | Description |
| :--- | :--- |
| `LocalProtocolError` | A protocol was violated by the client (e.g. missing Host header) [httpx/_exceptions.py:222-229](). |
| `RemoteProtocolError` | The protocol was violated by the server (e.g. malformed HTTP) [httpx/_exceptions.py:232-238](). |

Sources: [httpx/_exceptions.py:216-237]()

### Other Request Errors

*   `DecodingError`: Raised when response decoding fails due to malformed encoding [httpx/_exceptions.py:243-247]().
*   `TooManyRedirects`: Raised when a request exceeds the maximum redirect limit [httpx/_exceptions.py:249-253]().

## HTTP Status Error

`HTTPStatusError` is raised by `response.raise_for_status()` if the response has a 4xx or 5xx status code [httpx/_exceptions.py:258-263](). Unlike standard `RequestError` types, this exception includes both the `.request` and the `.response` properties [httpx/_exceptions.py:265-269]().

Sources: [httpx/_exceptions.py:258-269]()

## Independent Exceptions

*   `InvalidURL`: Raised when a URL is improperly formed or cannot be parsed [httpx/_exceptions.py:271-278]().
*   `CookieConflict`: Raised when multiple cookies exist for a single name during lookup [httpx/_exceptions.py:280-289]().

## Stream Errors

`StreamError` and its subclasses occur as a result of programming errors when accessing request or response streams in an invalid manner [httpx/_exceptions.py:291-307]().

| Exception Class | Description |
| :--- | :--- |
| `StreamConsumed` | Attempted to read content that has already been streamed [httpx/_exceptions.py:309-310](). |
| `StreamClosed` | Attempted to access a stream that has already been closed [httpx/_exceptions.py:313-314](). |
| `ResponseNotRead` | Attempted to access `response.content` before the response was read [httpx/_exceptions.py:317-321](). |
| `RequestNotRead` | Attempted to access `request.content` before the request was read [httpx/_exceptions.py:324-328](). |

Sources: [httpx/_exceptions.py:297-363]()

## Relationship to Transport System

HTTPX maps all exception classes exposed by the underlying `httpcore` library to its own hierarchy to ensure that users do not need to catch `httpcore` exceptions directly [tests/test_exceptions.py:14-18]().

```mermaid
graph LR
    subgraph "httpcore Space"
        HCE[httpcore.ConnectError]
        HCT[httpcore.ReadTimeout]
    end
    
    subgraph "httpx Space"
        HE[httpx.ConnectError]
        HT[httpx.ReadTimeout]
    end
    
    HCE -->|Mapped to| HE
    HCT -->|Mapped to| HT
```

Sources: [tests/test_exceptions.py:14-37](), [httpx/_exceptions.py:123-237]()

---

# Page: Handling Network Errors

# Handling Network Errors

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/__init__.py](httpx/__init__.py)
- [httpx/_exceptions.py](httpx/_exceptions.py)
- [tests/test_exceptions.py](tests/test_exceptions.py)

</details>



This document explains how to handle network-level failures in HTTPX, including timeouts, connection failures, and protocol errors. These are distinct from HTTP status errors (4xx, 5xx responses), which are covered in [HTTP Status Errors](#7.3). For the complete exception hierarchy, see [Exception Hierarchy](#7.1).

Network errors occur during the transport layer operations before a valid HTTP response is received. They inherit from `RequestError`, which serves as the base class for all exceptions that occur while issuing an HTTP request [httpx/_exceptions.py:107-110]().

## Network Error Categories

HTTPX organizes network errors into several categories based on the failure mode. All network exceptions inherit from `RequestError` [httpx/_exceptions.py:107-110]() and include a `.request` attribute containing the `Request` object that triggered the error [httpx/_exceptions.py:97-100]().

### Timeout Exceptions

Timeout errors occur when network operations exceed configured time limits. HTTPX provides granular timeout exceptions corresponding to different phases of the request lifecycle:

| Exception Class | Trigger Condition |
|----------------|-------------------|
| `ConnectTimeout` | Timed out while connecting to the host [httpx/_exceptions.py:140-144]() |
| `ReadTimeout` | Timed out while receiving data from the host [httpx/_exceptions.py:146-150]() |
| `WriteTimeout` | Timed out while sending data to the host [httpx/_exceptions.py:152-156]() |
| `PoolTimeout` | Timed out waiting to acquire a connection from the pool [httpx/_exceptions.py:158-162]() |
| `TimeoutException` | Base class for all timeout errors [httpx/_exceptions.py:132-137]() |

**Diagram: Timeout Exception Hierarchy**
```mermaid
graph TB
    subgraph "TimeoutExceptionHierarchy"
        TimeoutException["TimeoutException<br/>(Base)"]
        ConnectTimeout["ConnectTimeout<br/>connection establishment"]
        ReadTimeout["ReadTimeout<br/>reading response"]
        WriteTimeout["WriteTimeout<br/>writing request"]
        PoolTimeout["PoolTimeout<br/>pool acquisition"]
        
        TimeoutException --> ConnectTimeout
        TimeoutException --> ReadTimeout
        TimeoutException --> WriteTimeout
        TimeoutException --> PoolTimeout
    end
```

**Sources:** [httpx/_exceptions.py:132-162]()

### Connection and I/O Errors

Network errors occur when the underlying network operations fail. These inherit from `NetworkError` [httpx/_exceptions.py:167-172]():

| Exception Class | Description |
|----------------|-------------|
| `NetworkError` | Base class for network-related errors [httpx/_exceptions.py:167-172]() |
| `ConnectError` | Failed to establish a connection [httpx/_exceptions.py:187-191]() |
| `ReadError` | Failed to receive data from the network [httpx/_exceptions.py:175-179]() |
| `WriteError` | Failed to send data through the network [httpx/_exceptions.py:181-185]() |
| `CloseError` | Failed to close a connection [httpx/_exceptions.py:193-197]() |

**Diagram: Network Error Logic**
```mermaid
graph TB
    NetworkError["NetworkError<br/>(Base)"]
    ConnectError["ConnectError<br/>TCP connection failed"]
    ReadError["ReadError<br/>socket read failed"]
    WriteError["WriteError<br/>socket write failed"]
    CloseError["CloseError<br/>socket close failed"]
    
    NetworkError --> ConnectError
    NetworkError --> ReadError
    NetworkError --> WriteError
    NetworkError --> CloseError
```

**Sources:** [httpx/_exceptions.py:167-197]()

### Protocol and Proxy Errors

| Exception Class | Description |
|----------------|-------------|
| `ProtocolError` | The protocol was violated [httpx/_exceptions.py:215-219]() |
| `LocalProtocolError` | Protocol violated by the client [httpx/_exceptions.py:222-229]() |
| `RemoteProtocolError` | Protocol violated by the server [httpx/_exceptions.py:232-238]() |
| `UnsupportedProtocol` | Request to an unsupported protocol (e.g., ftp://) [httpx/_exceptions.py:208-213]() |
| `ProxyError` | Error establishing a proxy connection [httpx/_exceptions.py:202-206]() |

**Sources:** [httpx/_exceptions.py:202-238]()

## Exception Mapping Architecture

HTTPX delegates network operations to the `httpcore` library. To provide a consistent API, HTTPX maps `httpcore` exceptions to its own internal exception hierarchy. This mapping ensures that users only need to catch `httpx` exceptions even when the underlying failure comes from the transport layer.

**Diagram: httpcore to httpx Mapping**
```mermaid
flowchart TD
    subgraph "httpcore_Exceptions"
        hc_ConnectTimeout["httpcore.ConnectTimeout"]
        hc_ReadError["httpcore.ReadError"]
        hc_ProtocolError["httpcore.ProtocolError"]
    end
    
    subgraph "httpx_Exceptions"
        hx_ConnectTimeout["httpx.ConnectTimeout"]
        hx_ReadError["httpx.ReadError"]
        hx_ProtocolError["httpx.ProtocolError"]
    end
    
    hc_ConnectTimeout -- "mapped to" --> hx_ConnectTimeout
    hc_ReadError -- "mapped to" --> hx_ReadError
    hc_ProtocolError -- "mapped to" --> hx_ProtocolError
```

The validity of this mapping is verified by internal tests which ensure all exceptions exposed by `httpcore` have a corresponding class in `httpx` [tests/test_exceptions.py:14-37]().

**Sources:** [tests/test_exceptions.py:14-52]()

## Exception Handling Patterns

### Basic Exception Handling

The most common pattern is to catch `HTTPError` (the root of the hierarchy) or `RequestError` (for network-specific issues).

```python
import httpx

try:
    response = httpx.get("https://www.example.com")
except httpx.RequestError as exc:
    # All RequestError instances have access to the original request
    print(f"An error occurred while requesting {exc.request.url!r}.")
```

The `.request` property is automatically associated with the exception during the request lifecycle [httpx/_exceptions.py:97-105](). Attempting to access `.request` on an exception that hasn't been associated with one will raise a `RuntimeError` [httpx/_exceptions.py:98-99]().

**Sources:** [httpx/_exceptions.py:74-105](), [tests/test_exceptions.py:54-64]()

### Granular Timeout Handling

Since timeouts are split into specific phases, you can handle them differently based on where the failure occurred:

```python
try:
    httpx.get("https://example.com", timeout=httpx.Timeout(5.0, read=0.01))
except httpx.ConnectTimeout:
    # Handle failure to reach server
    pass
except httpx.ReadTimeout:
    # Handle slow response processing
    pass
```

**Sources:** [tests/test_exceptions.py:47-51](), [httpx/_exceptions.py:140-162]()

## Error Attribution

Every `HTTPError` (including `RequestError` and `HTTPStatusError`) is designed to carry a reference to the `Request` object that caused it. This is critical for debugging in asynchronous environments or when using connection pools where many requests are in flight.

- `HTTPError` provides the base `.request` property [httpx/_exceptions.py:97-105]().
- `HTTPStatusError` explicitly requires both `request` and `response` in its constructor [httpx/_exceptions.py:265-268]().
- `RequestError` allows passing the `request` during initialization [httpx/_exceptions.py:112-120]().

**Sources:** [httpx/_exceptions.py:74-120](), [httpx/_exceptions.py:258-269]()

---

# Page: HTTP Status Errors

# HTTP Status Errors

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [httpx/_status_codes.py](httpx/_status_codes.py)
- [tests/models/test_requests.py](tests/models/test_requests.py)
- [tests/models/test_responses.py](tests/models/test_responses.py)
- [tests/test_status_codes.py](tests/test_status_codes.py)

</details>



## Purpose and Scope

This document covers HTTP status code error handling in HTTPX, specifically the `raise_for_status()` method and the `HTTPStatusError` exception. This mechanism allows applications to convert non-successful HTTP responses into Python exceptions for explicit error handling.

For information about network-level errors (timeouts, connection failures), see [7.2 Handling Network Errors](). For an overview of HTTPX's complete exception hierarchy, see [7.1 Exception Hierarchy]().

---

## Overview

HTTPX provides explicit status code validation through the `response.raise_for_status()` method. Unlike automatic error raising (which HTTPX intentionally avoids), this approach requires developers to explicitly opt-in to exception-based error handling for HTTP status codes.

**Key Design Principle**: HTTPX treats all HTTP responses as valid responses, regardless of status code. Applications must explicitly call `raise_for_status()` to convert non-2xx status codes into exceptions.

### Status Flow and Error Dispatch

The following diagram illustrates how a raw response is processed and how `raise_for_status()` acts as a gateway for exception dispatch.

```mermaid
flowchart TD
    Request["httpx.Request"] --> Transport["Transport Layer"]
    Transport --> RawResponse["Raw HTTP Response<br/>(Any Status Code)"]
    RawResponse --> ResponseObj["httpx.Response Object"]
    
    ResponseObj --> UserCheck{User Calls<br/>raise_for_status()?}
    
    UserCheck -->|No| Properties["Access Properties<br/>status_code, text, json()"]
    UserCheck -->|Yes| StatusCheck{Status Code?}
    
    StatusCheck -->|"2xx"| ReturnResponse["Return Response<br/>(No Exception)"]
    StatusCheck -->|"1xx"| InfoError["Raise HTTPStatusError<br/>Informational response"]
    StatusCheck -->|"3xx"| RedirectError["Raise HTTPStatusError<br/>Redirect response"]
    StatusCheck -->|"4xx"| ClientError["Raise HTTPStatusError<br/>Client error"]
    StatusCheck -->|"5xx"| ServerError["Raise HTTPStatusError<br/>Server error"]
    
    Properties --> Application["Application Logic"]
    ReturnResponse --> Application
    InfoError --> ExceptionHandler["Exception Handler"]
    RedirectError --> ExceptionHandler
    ClientError --> ExceptionHandler
    ServerError --> ExceptionHandler
```

**Sources**: [tests/models/test_responses.py:91-147]()

---

## The raise_for_status() Method

The `raise_for_status()` method validates the HTTP status code and raises `HTTPStatusError` for any response that is not a 2xx success code.

### Method Signature

```python
response.raise_for_status() -> Response
```

The method returns the response instance itself, enabling inline usage and method chaining.

### Status Code Categorization Logic

HTTPX uses the `httpx._status_codes.codes` class (an `IntEnum`) to categorize status codes. This class provides helper methods like `is_error`, `is_client_error`, and `is_server_error` used during the validation process.

```mermaid
graph TB
    subgraph "Status Code Ranges (httpx._status_codes.codes)"
        S1xx["1xx Informational<br/>is_informational() = True"]
        S2xx["2xx Success<br/>is_success() = True"]
        S3xx["3xx Redirection<br/>is_redirect() = True"]
        S4xx["4xx Client Error<br/>is_client_error() = True"]
        S5xx["5xx Server Error<br/>is_server_error() = True"]
    end
    
    RaiseForStatus["raise_for_status()"]
    
    S1xx -->|Raises| HTTPStatusError1["HTTPStatusError<br/>Informational response"]
    S2xx -->|Returns| ResponseOK["Response Instance<br/>No Exception"]
    S3xx -->|Raises| HTTPStatusError3["HTTPStatusError<br/>Redirect response"]
    S4xx -->|Raises| HTTPStatusError4["HTTPStatusError<br/>Client error"]
    S5xx -->|Raises| HTTPStatusError5["HTTPStatusError<br/>Server error"]
    
    RaiseForStatus --> S1xx
    RaiseForStatus --> S2xx
    RaiseForStatus --> S3xx
    RaiseForStatus --> S4xx
    RaiseForStatus --> S5xx
```

**Sources**: [httpx/_status_codes.py:46-85](), [tests/models/test_responses.py:91-141]()

---

## Response Status Properties

HTTPX provides boolean properties on the `httpx.Response` object for checking status code categories without raising exceptions. These properties delegate to the `codes` utility class.

### Available Properties

| Property | Status Codes | Logic Implementation |
|----------|-------------|----------------------|
| `is_informational` | 100-199 | `100 <= value <= 199` |
| `is_success` | 200-299 | `200 <= value <= 299` |
| `is_redirect` | 300-399 | `300 <= value <= 399` |
| `is_client_error` | 400-499 | `400 <= value <= 499` |
| `is_server_error` | 500-599 | `500 <= value <= 599` |
| `is_error` | 400-599 | `400 <= value <= 599` |

### Usage Examples

```python
response = httpx.get('https://example.org/404')

# Check without raising exceptions
if response.is_client_error:
    print(f"Client error: {response.status_code}")

if response.is_error:
    print("Either 4xx or 5xx error")
```

**Sources**: [httpx/_status_codes.py:46-85](), [tests/models/test_responses.py:31-43](), [tests/models/test_responses.py:120-134]()

---

## HTTPStatusError Exception

The `HTTPStatusError` exception is raised by `raise_for_status()` for non-2xx status codes. It provides access to both the `httpx.Request` and `httpx.Response` objects.

### Exception Structure

```mermaid
classDiagram
    class HTTPStatusError {
        +Request request
        +Response response
        +str message
        __init__(message, request, response)
        __str__() str
    }
    
    class Request {
        +str method
        +URL url
        +Headers headers
    }
    
    class Response {
        +int status_code
        +str reason_phrase
        +Headers headers
        +bytes content
    }
    
    HTTPStatusError --> Request : "refers to"
    HTTPStatusError --> Response : "refers to"
```

### Accessing Exception Information

```python
import httpx

try:
    response = httpx.get('https://example.org/403')
    response.raise_for_status()
except httpx.HTTPStatusError as exc:
    # Access the request that caused the error
    assert exc.request.method == "GET"
    
    # Access the error response
    assert exc.response.status_code == 403
    print(f"Response body: {exc.response.text}")
```

**Sources**: [tests/models/test_responses.py:91-141](), [tests/models/test_requests.py:9-11]()

---

## Error Messages and Information

`HTTPStatusError` generates specific error messages based on the status category. These messages include the status code, the reason phrase, the target URL, and a link to MDN documentation for that specific code.

### Error Message Categories

| Category | Format |
|----------|--------|
| **Informational (1xx)** | `Informational response '101 Switching Protocols' for url '...'` |
| **Redirect (3xx)** | `Redirect response '303 See Other' for url '...'. Redirect location: '...'` |
| **Client Error (4xx)** | `Client error '403 Forbidden' for url '...'` |
| **Server Error (5xx)** | `Server error '500 Internal Server Error' for url '...'` |

The reason phrases are retrieved using `codes.get_reason_phrase(value)`.

**Sources**: [tests/models/test_responses.py:103-140](), [httpx/_status_codes.py:39-43]()

---

## Request Requirement

The `raise_for_status()` method strictly requires that the `Response` object has an associated `Request` instance. This association is typically handled automatically when using a `Client` or top-level functions, but must be provided manually when constructing `Response` objects directly.

```python
# This raises RuntimeError because request is missing
response = httpx.Response(404)
try:
    response.raise_for_status()
except RuntimeError:
    print("Request instance not set")

# Proper manual construction
request = httpx.Request("GET", "https://example.org")
response = httpx.Response(404, request=request)
response.raise_for_status()  # Raises HTTPStatusError correctly
```

**Sources**: [tests/models/test_responses.py:143-147](), [tests/models/test_responses.py:31-36]()

---

## Status Code Constants

HTTPX provides a comprehensive set of status code constants via `httpx.codes`. These constants support both uppercase and lowercase access for compatibility with other libraries like `requests`.

```python
assert httpx.codes.NOT_FOUND == 404
assert httpx.codes.not_found == 404
assert httpx.codes.get_reason_phrase(404) == "Not Found"
```

The `codes` class is an `IntEnum` populated from multiple RFCs including RFC 7231 (HTTP/1.1) and RFC 7540 (HTTP/2).

**Sources**: [httpx/_status_codes.py:8-26](), [httpx/_status_codes.py:161-162](), [tests/test_status_codes.py:4-24]()

---

# Page: Development

# Development

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.gitignore](.gitignore)
- [LICENSE.md](LICENSE.md)
- [docs/advanced/proxies.md](docs/advanced/proxies.md)
- [docs/contributing.md](docs/contributing.md)
- [docs/http2.md](docs/http2.md)
- [scripts/check](scripts/check)
- [scripts/install](scripts/install)
- [scripts/lint](scripts/lint)
- [scripts/sync-version](scripts/sync-version)
- [scripts/test](scripts/test)

</details>



This document provides a comprehensive guide for developers working on the httpx codebase itself, including setting up the development environment, understanding the testing infrastructure, and navigating the build and release processes. This covers the internal development workflows and tooling used to maintain and extend httpx.

For information about using httpx as a library in your own projects, see [Basic Usage](#2). For details about the repository structure and key modules, see [Repository Structure](#8.1).

## Development Environment Setup

The httpx development environment uses a standardized approach with pinned tooling dependencies and automated setup scripts. The project follows a philosophy of pinning development tools while keeping package dependencies unpinned to ensure compatibility with the latest versions.

### Development Dependencies

The development environment is configured through two main files: `requirements.txt` for development tooling and `pyproject.toml` for build system configuration.

```mermaid
graph TB
    DevSetup["Development Setup"]
    RequirementsTxt["requirements.txt"]
    PyprojectToml["pyproject.toml"]
    InstallScript["scripts/install"]
    
    DevSetup --> RequirementsTxt
    DevSetup --> PyprojectToml
    DevSetup --> InstallScript
    
    RequirementsTxt --> TestingTools["Testing Tools<br/>pytest, coverage, ruff, mypy"]
    RequirementsTxt --> DocsTools["Documentation Tools<br/>mkdocs, mkautodoc, mkdocs-material"]
    RequirementsTxt --> PackagingTools["Packaging Tools<br/>build, twine"]
    RequirementsTxt --> OptionalDeps["Optional Dependencies<br/>cryptography, trio, uvicorn"]
    
    PyprojectToml --> BuildBackend["hatchling build backend"]
    PyprojectToml --> ProjectMetadata["Project Metadata"]
    PyprojectToml --> OptionalExtras["Optional Extras<br/>brotli, cli, http2, socks, zstd"]
    
    InstallScript --> VirtualEnv["Virtual Environment Setup"]
    InstallScript --> DepInstallation["Dependency Installation"]
```

Sources: [docs/contributing.md:52-57](), [scripts/install:1-20]()

The development dependencies include several categories of tools:

| Category | Tools | Purpose |
|----------|-------|---------|
| Testing | `pytest`, `coverage` | Test execution and coverage reporting |
| Code Quality | `ruff`, `mypy` | Linting, formatting, and type checking |
| Documentation | `mkdocs`, `mkdocs-material` | Documentation site generation |
| Packaging | `build`, `twine` | Package building and PyPI publishing |
| Testing Dependencies | `trio`, `cryptography`, `uvicorn` | Async testing and server mocking |

### Setup Process

The development setup follows a simple workflow using shell scripts located in the `scripts/` directory:

1. **Initial Setup**: Run `scripts/install` to set up the development environment and virtual environment. [scripts/install:1-20]()
2. **Testing**: Use `scripts/test` for running tests with coverage. [scripts/test:1-19]()
3. **Code Quality**: Use `scripts/lint` for auto-formatting and `scripts/check` for validation. [scripts/lint:1-13](), [scripts/check:1-15]()
4. **Documentation**: Use `scripts/docs` for local documentation preview. [docs/contributing.md:98-102]()

Sources: [docs/contributing.md:64-102](), [scripts/install:1-20]()

## Testing Infrastructure

The testing system is built around `pytest` with comprehensive coverage requirements and support for multiple Python versions and async frameworks.

### Test Configuration and Execution

The test execution follows a standardized workflow implemented in the `scripts/test` shell script, which automatically handles virtual environment detection and pre-test checks.

```mermaid
graph LR
    TestScript["scripts/test"]
    
    TestScript --> VenvDetection["Virtual Environment Detection"]
    TestScript --> PreChecks["Pre-test Checks"]
    TestScript --> CoverageRun["Coverage Execution"]
    TestScript --> PostProcessing["Post-processing"]
    
    VenvDetection --> PrefixSet["Set PREFIX variable"]
    
    PreChecks --> GitHubCheck["Check GITHUB_ACTIONS env"]
    GitHubCheck --> CheckScript["Run scripts/check"]
    
    CoverageRun --> PytestExecution["${PREFIX}coverage run -m pytest"]
    
    PostProcessing --> CoverageReport["scripts/coverage"]
```

Sources: [scripts/test:1-19]()

The test suite has specific requirements for proper execution:
- **Port Availability**: Tests spawn servers on ports 8000 and 8001. [docs/contributing.md:70-72]()
- **Coverage Threshold**: 100% test coverage is required for CI to pass. [docs/contributing.md:151]()
- **Execution**: Any additional arguments to `scripts/test` are passed directly to `pytest`. [docs/contributing.md:74-80]()

For more details, see [Testing](#8.2).

## Code Quality and Linting

The project uses multiple tools for maintaining code quality, executed via shell scripts.

### Quality Assurance Workflow

The quality assurance process integrates into the development workflow through automated scripts:

1. **Auto-formatting**: `scripts/lint` applies automatic code formatting using `ruff`. [scripts/lint:11-12]()
2. **Validation**: `scripts/check` runs all quality checks, including `ruff format --diff`, `mypy`, and `ruff check`. [scripts/check:11-14]()
3. **Version Sync**: The `scripts/sync-version` script ensures the version in `httpx/__version__.py` matches the latest entry in `CHANGELOG.md`. [scripts/sync-version:1-12]()

Sources: [docs/contributing.md:82-92](), [scripts/check:1-15](), [scripts/lint:1-13]()

## Build System and Packaging

The httpx project uses a modern Python build system. Package metadata and optional dependency groups are defined to support various features.

| Optional Group | Purpose |
|----------------|---------|
| `brotli` | Brotli compression support |
| `cli` | Command-line interface |
| `http2` | HTTP/2 protocol support. [docs/http2.md:30-32]() |
| `socks` | SOCKS proxy support. [docs/advanced/proxies.md:73-77]() |
| `zstd` | Zstandard compression |

### Release Process

The release process is managed by maintainers and involves:
1. Updating the `CHANGELOG.md` following the [keepachangelog](https://keepachangelog.com/en/1.0.0/) format. [docs/contributing.md:159-165]()
2. Bumping the version in `httpx/__version__.py`. [docs/contributing.md:166]()
3. Creating a new GitHub release, which triggers an automated upload to PyPI. [docs/contributing.md:170-177]()
4. Manual publishing via `scripts/publish` if the automated job fails. [docs/contributing.md:179-180]()

For more details, see [CI/CD Pipelines](#8.3).

## Development Proxy Testing

For development scenarios involving proxy testing, the project suggests using `mitmproxy`.

```mermaid
graph LR
    ProxySetup["Proxy Development Setup"]
    
    ProxySetup --> CertGeneration["Certificate Generation"]
    ProxySetup --> ProxyServer["Proxy Server Setup"]
    ProxySetup --> ClientConfig["Client Configuration"]
    
    CertGeneration --> TrustmeCLI["trustme-cli installation"]
    TrustmeCLI --> CertFiles["Generate server.pem, server.key, client.pem"]
    
    ProxyServer --> MitmproxyInstall["pip install mitmproxy"]
    MitmproxyInstall --> StartServer["mitmproxy --certs ..."]
    
    ClientConfig --> ProxyParam["httpx.Client(proxy='...')"]
```

Sources: [docs/contributing.md:182-200](), [docs/advanced/proxies.md:1-15]()

This setup enables developers to test:
- **Forwarding**: The proxy makes the request for the client. [docs/advanced/proxies.md:61]()
- **Tunnelling**: The proxy establishes a TCP connection (required for HTTPS over HTTP proxies). [docs/advanced/proxies.md:62]()
- **SOCKS**: Testing SOCKS5 proxy support. [docs/advanced/proxies.md:79-83]()

Sources: [docs/contributing.md:182-200](), [docs/advanced/proxies.md:52-83]()

---

# Page: Repository Structure

# Repository Structure

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.gitignore](.gitignore)
- [LICENSE.md](LICENSE.md)
- [pyproject.toml](pyproject.toml)
- [requirements.txt](requirements.txt)
- [scripts/check](scripts/check)
- [scripts/install](scripts/install)
- [scripts/lint](scripts/lint)
- [scripts/sync-version](scripts/sync-version)
- [scripts/test](scripts/test)

</details>



This document provides a comprehensive guide to the `httpx` codebase organization and key modules. It is designed for developers who want to contribute to `httpx` or understand its internal architecture. For information about using `httpx` as a library, see the usage documentation in sections 2-7. For specific development workflows like testing and CI/CD, see [Testing](#8.2) and [CI/CD Pipelines](#8.3).

## Repository Layout

The `httpx` repository follows a standard Python package structure with clear separation between source code, tests, documentation, and development infrastructure.

```mermaid
graph TD
    subgraph "Repository Root"
        pyproject["pyproject.toml<br/>Build System & Metadata"]
        requirements["requirements.txt<br/>Development Dependencies"]
        changelog["CHANGELOG.md"]
        readme["README.md"]
    end
    
    subgraph "Source Code"
        httpx_pkg["httpx/<br/>Main Package"]
        version["httpx/__version__.py"]
        init["httpx/__init__.py"]
        core_modules["httpx/_*.py<br/>Core Implementation"]
    end
    
    subgraph "Development Infrastructure"
        scripts_dir["scripts/<br/>Development Scripts"]
        test_script["scripts/test"]
        lint_script["scripts/lint"]
        check_script["scripts/check"]
        install_script["scripts/install"]
    end
    
    subgraph "Testing & Documentation"
        tests_dir["tests/<br/>Test Suite"]
        docs_dir["docs/<br/>Documentation Source"]
    end
    
    pyproject --> httpx_pkg
    requirements --> scripts_dir
    scripts_dir --> tests_dir
    scripts_dir --> docs_dir
```

**Sources:** [pyproject.toml:70-76](), [requirements.txt:1-30](), [scripts/test:1-19](), [scripts/check:1-14]()

## Core Package Architecture

The `httpx` package is organized around architectural layers, with each major component implemented in dedicated modules. The package uses a private module naming convention (prefixed with `_`) for internal implementation details while exposing a clean public API via `__init__.py`.

```mermaid
graph TB
    subgraph "httpx Package Structure"
        init_py["__init__.py<br/>Public API Exports"]
        version_py["__version__.py<br/>Version String"]
        
        subgraph "Core Implementation Modules"
            client_py["_client.py<br/>Client & AsyncClient Classes"]
            models_py["_models.py<br/>Request, Response, URL"]
            transports_py["_transports.py<br/>Transport Implementations"]
            config_py["_config.py<br/>Configuration Classes"]
            auth_py["_auth.py<br/>Authentication Classes"]
            content_py["_content.py<br/>Encoding/Decoding"]
            utils_py["_utils.py<br/>Utility Functions"]
            exceptions_py["_exceptions.py<br/>Exception Hierarchy"]
        end
        
        subgraph "Specialized Modules"
            api_py["_api.py<br/>Top-Level Functions"]
            status_codes_py["_status_codes.py<br/>HTTP Status Constants"]
            decoders_py["_decoders.py<br/>Content Decompression"]
        end
    end
    
    init_py --> client_py
    init_py --> models_py
    init_py --> api_py
    client_py --> transports_py
    client_py --> config_py
    client_py --> auth_py
    models_py --> content_py
    models_py --> decoders_py
```

**Sources:** [pyproject.toml:67-68](), [pyproject.toml:106-106]()

## Development Infrastructure

The repository uses shell scripts and modern Python tooling to automate common development tasks. All development scripts are located in the `scripts/` directory and provide consistent interfaces across different environments (local vs CI).

### Build System Configuration

The project uses `hatchling` as its build backend with sophisticated readme generation and metadata management via `hatch-fancy-pypi-readme`.

| Configuration | File | Purpose |
|---------------|------|---------|
| Build Backend | `pyproject.toml` | Hatch-based build system [pyproject.toml:1-3]() |
| Dependencies | `pyproject.toml` | Core and optional dependencies definition [pyproject.toml:30-56]() |
| Dev Dependencies | `requirements.txt` | Pinned development tooling versions [requirements.txt:1-30]() |
| Tool Configuration | `pyproject.toml` | Configuration for ruff, mypy, pytest, coverage [pyproject.toml:98-133]() |

**Sources:** [pyproject.toml:1-3](), [pyproject.toml:78-93](), [requirements.txt:1-5]()

### Development Scripts

The following scripts are used to maintain code quality:

```mermaid
graph LR
    subgraph "Development Workflow"
        install["scripts/install<br/>Environment Setup"]
        test["scripts/test<br/>Test Execution"]
        lint["scripts/lint<br/>Code Formatting"]
        check["scripts/check<br/>Quality Checks"]
        sync_version["scripts/sync-version<br/>Version Consistency"]
    end
    
    subgraph "Underlying Tools"
        pytest["pytest<br/>Test Runner"]
        coverage["coverage<br/>Test Coverage"]
        ruff["ruff<br/>Linting & Formatting"]
        mypy["mypy<br/>Type Checking"]
    end
    
    install --> test
    test --> pytest
    test --> coverage
    lint --> ruff
    check --> ruff
    check --> mypy
    check --> sync_version
```

The `scripts/test` script integrates coverage and optionally runs quality checks if not running in a GitHub Actions environment:

```sh
if [ -z $GITHUB_ACTIONS ]; then
    scripts/check
fi

${PREFIX}coverage run -m pytest "$@"
```

**Sources:** [scripts/test:10-14](), [scripts/check:1-14](), [scripts/lint:1-13](), [scripts/install:1-20]()

## Testing Structure

The test suite is organized to cover unit tests, integration tests, and compatibility checks.

### Test Configuration

The `pytest` configuration includes custom markers and strict warning handling. Notably, it includes a `network` marker for tests requiring external connectivity, which is often disabled in restricted build environments.

```toml
[tool.pytest.ini_options]
addopts = "-rxXs"
filterwarnings = [
  "error",
  "ignore: You seem to already have a custom sys.excepthook handler installed..."
]
markers = [
  "copied_from(source, changes=None): mark test as copied from somewhere else",
  "network: marks tests which require network connection."
]
```

**Sources:** [pyproject.toml:117-128]()

## Configuration Files

### Project Metadata and Build System

The `pyproject.toml` file defines the project identity and its runtime requirements. `httpx` requires Python 3.9+ and depends on several low-level libraries for networking and data handling.

```toml
[project]
name = "httpx"
requires-python = ">=3.9"
dependencies = [
    "certifi",
    "httpcore==1.*",
    "anyio",
    "idna",
]
```

**Sources:** [pyproject.toml:5-35]()

### Optional Dependencies (Extras)

The project defines several optional dependency groups to support different protocols and formats without bloating the core installation:

| Group | Dependencies | Purpose |
|-------|--------------|---------|
| `brotli` | `brotli` or `brotlicffi` | Brotli decompression support [pyproject.toml:39-42]() |
| `cli` | `click`, `pygments`, `rich` | Command-line interface [pyproject.toml:43-47]() |
| `http2` | `h2` | HTTP/2 protocol support [pyproject.toml:48-50]() |
| `socks` | `socksio` | SOCKS proxy support [pyproject.toml:51-53]() |
| `zstd` | `zstandard` | Zstandard compression [pyproject.toml:54-56]() |

## External Dependencies

The `httpx` architecture separates high-level logic from low-level implementation by delegating to specialized libraries.

```mermaid
graph TB
    subgraph "Core Dependencies"
        httpcore["httpcore==1.*<br/>Low-level HTTP Implementation"]
        anyio["anyio<br/>Async Abstraction Layer"]
        certifi["certifi<br/>SSL Certificate Bundle"]
        idna["idna<br/>IDN Support"]
    end
    
    subgraph "httpx Core"
        client_impl["Client / AsyncClient"]
        transport_layer["Transport Layer"]
        ssl_handling["SSL Contexts"]
    end
    
    httpcore --> transport_layer
    anyio --> client_impl
    certifi --> ssl_handling
```

**Sources:** [pyproject.toml:30-35](), [requirements.txt:5-5]()

---

# Page: Testing

# Testing

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.gitignore](.gitignore)
- [LICENSE.md](LICENSE.md)
- [scripts/install](scripts/install)
- [scripts/test](scripts/test)
- [tests/concurrency.py](tests/concurrency.py)
- [tests/conftest.py](tests/conftest.py)
- [tests/test_exported_members.py](tests/test_exported_members.py)

</details>



This document covers the testing infrastructure, tools, and practices used in the `httpx` codebase. It explains how to run tests, understand the test fixtures, write new tests, and work with the testing utilities provided by the project.

For information about the CI/CD pipelines that run these tests, see [CI/CD Pipelines](#8.3). For details about the overall repository structure, see [Repository Structure](#8.1).

## Test Infrastructure Overview

The `httpx` testing system is built around `pytest` and includes a comprehensive set of fixtures, mock servers, and utilities to test HTTP client functionality across different scenarios.

### Core Testing Architecture

```mermaid
graph TB
    subgraph "Test Execution Layer"
        TestScript["scripts/test"]
        Coverage["coverage run"]
        Pytest["pytest"]
    end
    
    subgraph "Test Configuration"
        Conftest["tests/conftest.py"]
        Fixtures["Test Fixtures"]
        EnvCleanup["clean_environ"]
    end
    
    subgraph "Test Server Infrastructure" 
        TestServerClass["TestServer"]
        ASGIApp["app (ASGI)"]
        UvicornServer["uvicorn.Server"]
        ServerFixture["server fixture"]
    end
    
    subgraph "SSL/TLS Testing"
        TrustmeCA["trustme.CA"]
        CertFixtures["Certificate Fixtures"]
        SSLContext["SSL Context"]
    end
    
    subgraph "Test Utilities"
        MockTransport["MockTransport"]
        ASGITransport["ASGITransport"] 
        WSGITransport["WSGITransport"]
        ConcurrencyUtils["tests/concurrency.py"]
    end
    
    TestScript --> Coverage
    Coverage --> Pytest
    Pytest --> Conftest
    Conftest --> Fixtures
    Conftest --> EnvCleanup
    
    Fixtures --> ServerFixture
    ServerFixture --> TestServerClass
    TestServerClass --> UvicornServer
    TestServerClass --> ASGIApp
    
    Fixtures --> CertFixtures
    CertFixtures --> TrustmeCA
    
    Conftest --> ConcurrencyUtils
```

Sources: [tests/conftest.py:1-288](), [scripts/test:1-19](), [tests/concurrency.py:1-16]()

### Test Server Components

The test infrastructure includes a custom `TestServer` class (extending `uvicorn.Server`) that runs an ASGI application providing various endpoints for testing:

```mermaid
graph TB
    subgraph "ASGI Test Application (tests/conftest.py)"
        AppFunction["app"]
        HelloWorld["hello_world"]
        SlowResponse["slow_response"] 
        StatusCode["status_code"]
        EchoBody["echo_body"]
        EchoBinary["echo_binary"]
        EchoHeaders["echo_headers"]
        Redirect301["redirect_301"]
        HelloWorldJSON["hello_world_json"]
    end
    
    subgraph "TestServer Class"
        TestServerClass["TestServer"]
        URLProperty["url property"]
        SignalHandlers["install_signal_handlers"]
    end
    
    subgraph "Server Fixtures"
        ServerFixture["server fixture"]
        ServeInThread["serve_in_thread"]
        Threading["threading.Thread"]
    end
    
    AppFunction --> HelloWorld
    AppFunction --> SlowResponse
    AppFunction --> StatusCode
    AppFunction --> EchoBody
    AppFunction --> EchoBinary
    AppFunction --> EchoHeaders
    AppFunction --> Redirect301
    AppFunction --> HelloWorldJSON
    
    ServerFixture --> ServeInThread
    ServeInThread --> Threading
    ServeInThread --> TestServerClass
    TestServerClass --> AppFunction
```

Sources: [tests/conftest.py:59-287]()

## Running Tests

### Basic Test Execution

The primary way to run tests is through the `scripts/test` shell script, which handles coverage collection and environment setup:

```bash
$ scripts/test
```

This script executes the following sequence:
1. Runs code quality checks via `scripts/check` (unless in GitHub Actions) [scripts/test:10-12]()
2. Executes `pytest` with `coverage run -m` [scripts/test:14-14]()
3. Generates coverage reports (unless in GitHub Actions) [scripts/test:16-18]()

### Environment Management

The `clean_environ` fixture ensures test isolation by managing environment variables. It is scoped to the function level and applied automatically to every test:

```python
@pytest.fixture(scope="function", autouse=True)
def clean_environ():
    """Keeps os.environ clean for every test without having to mock os.environ"""
```

It captures the original `os.environ` and clears specific variables defined in `ENVIRONMENT_VARIABLES` (like `HTTP_PROXY`, `SSL_CERT_FILE`, etc.) to prevent local developer configurations from leaking into the test suite [tests/conftest.py:23-48]().

## Test Fixtures and Utilities

### SSL Certificate Fixtures

The testing infrastructure provides comprehensive SSL certificate management using the `trustme` library to facilitate testing of HTTPS connections and certificate verification:

| Fixture | Definition | Purpose |
|---------|------------|---------|
| `cert_authority` | [tests/conftest.py:186-187]() | Root certificate authority |
| `localhost_cert` | [tests/conftest.py:190-192]() | Certificate issued for `localhost` |
| `cert_pem_file` | [tests/conftest.py:196-199]() | Temporary PEM file for the certificate chain |
| `cert_private_key_file` | [tests/conftest.py:202-205]() | Temporary file for the private key |
| `cert_encrypted_private_key_file` | [tests/conftest.py:208-222]() | Password-protected private key file |

### Concurrency Utilities

The `tests/concurrency.py` module provides environment-agnostic utilities to handle both `asyncio` and `trio` within the test suite. The `sleep` function detects the current async library using `sniffio` and calls the appropriate sleep implementation [tests/concurrency.py:11-16]().

## Test Endpoint Catalog

The ASGI `app` defined in `tests/conftest.py` routes requests to specific handlers based on the URL path:

| Path Pattern | Handler Function | Purpose |
|--------------|------------------|---------|
| `/slow_response` | `slow_response` | Triggers a 1.0s delay to test read timeouts [tests/conftest.py:101-110]() |
| `/status/{code}` | `status_code` | Returns the specified HTTP status code [tests/conftest.py:113-122]() |
| `/echo_body` | `echo_body` | Reads the request body and echoes it back [tests/conftest.py:125-141]() |
| `/echo_binary` | `echo_binary` | Echoes body with `application/octet-stream` [tests/conftest.py:144-160]() |
| `/echo_headers` | `echo_headers` | Returns request headers as a JSON object [tests/conftest.py:163-176]() |
| `/redirect_301` | `redirect_301` | Returns a 301 Moved Permanently to `/` [tests/conftest.py:178-182]() |
| `/json` | `hello_world_json` | Returns a JSON "Hello world" response [tests/conftest.py:90-98]() |
| Default | `hello_world` | Returns a plain text "Hello, world!" [tests/conftest.py:79-87]() |

## Test Organization

### Directory Structure

The `tests/` directory contains all test modules, typically prefixed with `test_`.

- `tests/conftest.py`: Contains global fixtures, the ASGI test app, and the `TestServer` class [tests/conftest.py:1-288]().
- `tests/concurrency.py`: Async utilities for testing across different backends [tests/concurrency.py:1-16]().
- `tests/test_exported_members.py`: Ensures all public members are correctly listed in `httpx.__all__` [tests/test_exported_members.py:1-14]().

### Mock Transport Testing

While `TestServer` is used for integration testing over actual network sockets, `httpx` also utilizes `MockTransport` for unit testing logic without a server. This allows defining a handler function that receives a `Request` and returns a `Response` directly [tests/conftest.py:59-77]().

Sources: [tests/conftest.py:1-288](), [tests/concurrency.py:1-16](), [scripts/test:1-19]()

---

# Page: CI/CD Pipelines

# CI/CD Pipelines

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.github/dependabot.yml](.github/dependabot.yml)
- [.github/workflows/publish.yml](.github/workflows/publish.yml)
- [.github/workflows/test-suite.yml](.github/workflows/test-suite.yml)
- [docs/async.md](docs/async.md)
- [scripts/build](scripts/build)
- [scripts/publish](scripts/publish)

</details>



This document describes the continuous integration and continuous deployment (CI/CD) infrastructure for the HTTPX project. It covers the GitHub Actions workflows for testing, building, and publishing releases, along with the supporting scripts and configuration.

For information about the testing infrastructure itself (pytest configuration, fixtures, test organization), see [Testing](#8.2). For details about the development tooling and repository structure, see [Repository Structure](#8.1).

## Overview

The HTTPX project uses GitHub Actions for CI/CD automation with two primary workflows:

1.  **Test Suite Workflow** - Runs on every push to `master` and pull requests, executing tests across multiple Python versions.
2.  **Publish Workflow** - Triggers on git tags, building packages and deploying to PyPI.

All workflows delegate to shell scripts in the `scripts/` directory for portability and local reproducibility.

## GitHub Actions Workflows

### Test Suite Workflow Structure

The test suite workflow is defined in [.github/workflows/test-suite.yml:1-35]() and orchestrates automated testing for all code changes.

**Diagram: Test Suite Execution Flow**
```mermaid
graph TB
    Trigger["Trigger Events<br/>push to master<br/>pull_request"]
    Matrix["Test Matrix<br/>Python 3.9-3.13"]
    Checkout["actions/checkout@v4"]
    SetupPython["actions/setup-python@v6"]
    Install["scripts/install"]
    Check["scripts/check"]
    Build["scripts/build"]
    Test["scripts/test"]
    Coverage["scripts/coverage"]
    
    Trigger --> Matrix
    Matrix --> Checkout
    Checkout --> SetupPython
    SetupPython --> Install
    Install --> Check
    Check --> Build
    Build --> Test
    Test --> Coverage
    
    Install -.installs.-> Deps["requirements.txt<br/>pytest, ruff, mypy<br/>coverage, etc."]
    Check -.runs.-> Linting["ruff check/format<br/>mypy type checking"]
    Build -.creates.-> Artifacts["wheel and sdist<br/>docs build"]
    Test -.executes.-> PyTest["pytest test suite<br/>all test modules"]
    Coverage -.enforces.-> Threshold["coverage threshold<br/>configured in<br/>pyproject.toml"]
```

**Sources:** [.github/workflows/test-suite.yml:1-35]()

#### Workflow Triggers

The test suite runs on:
*   **Push events**: Any push to the `master` branch ([.github/workflows/test-suite.yml:5-6]()).
*   **Pull requests**: PRs targeting `master` or version branches ([.github/workflows/test-suite.yml:7-8]()).

#### Test Matrix Configuration

The workflow uses a matrix strategy to test across five Python versions ([.github/workflows/test-suite.yml:15-17]()):

| Python Version | Status |
| :--- | :--- |
| 3.9 | Minimum supported version |
| 3.10 | Stable |
| 3.11 | Stable |
| 3.12 | Stable |
| 3.13 | Latest, pre-releases allowed ([.github/workflows/test-suite.yml:24]()) |

Each matrix job runs independently on `ubuntu-latest` runners ([.github/workflows/test-suite.yml:13]()).

**Sources:** [.github/workflows/test-suite.yml:15-17](), [.github/workflows/test-suite.yml:24]()

#### Pipeline Stages

The test pipeline executes sequential stages ([.github/workflows/test-suite.yml:19-34]()):

1.  **Checkout**: Clones the repository using `actions/checkout@v4`.
2.  **Python Setup**: Installs the specified Python version using `actions/setup-python@v6`.
3.  **Install dependencies**: Runs `scripts/install` to set up the environment ([.github/workflows/test-suite.yml:25-26]()).
4.  **Run linting checks**: Runs `scripts/check` for static analysis ([.github/workflows/test-suite.yml:27-28]()).
5.  **Build package & docs**: Runs `scripts/build` to verify distribution and documentation builds ([.github/workflows/test-suite.yml:29-30]()).
6.  **Run tests**: Runs `scripts/test` to execute the pytest suite ([.github/workflows/test-suite.yml:31-32]()).
7.  **Enforce coverage**: Runs `scripts/coverage` to ensure code coverage standards are met ([.github/workflows/test-suite.yml:33-34]()).

**Sources:** [.github/workflows/test-suite.yml:19-34]()

### Publish Workflow Structure

The publish workflow is defined in [.github/workflows/publish.yml:1-30]() and handles automated releases to PyPI and documentation deployment.

**Diagram: Publish Workflow Data Flow**
```mermaid
graph TB
    TagPush["Git Tag Push<br/>any tag pattern"]
    Environment["GitHub Environment<br/>name: deploy"]
    Checkout["actions/checkout@v4"]
    SetupPython["actions/setup-python@v6<br/>Python 3.9"]
    Install["scripts/install"]
    Build["scripts/build"]
    Publish["scripts/publish"]
    
    TagPush --> Environment
    Environment --> Checkout
    Checkout --> SetupPython
    SetupPython --> Install
    Install --> Build
    Build --> Publish
    
    Environment -.provides.-> Secrets["PYPI_TOKEN<br/>secret"]
    Build -.creates.-> Packages["dist/*.whl<br/>dist/*.tar.gz"]
    Publish -.uses.-> Twine["twine upload<br/>to PyPI"]
    Publish -.deploys.-> Docs["MkDocs to<br/>GitHub Pages"]
    Secrets --> Publish
```

**Sources:** [.github/workflows/publish.yml:1-30]()

#### Workflow Triggers

The publish workflow triggers exclusively on tag pushes ([.github/workflows/publish.yml:4-6]()):

```yaml
on:
  push:
    tags:
      - '*'
```

Any tag matching the wildcard pattern `*` will initiate a release.

#### Deployment Environment

The workflow uses a GitHub environment named `deploy` ([.github/workflows/publish.yml:13-14]()) which provides protection rules and access to the `PYPI_TOKEN` secret.

#### Publishing Process

The publish job runs on `ubuntu-latest` with Python 3.9 ([.github/workflows/publish.yml:18-20]()) and executes:

1.  **Install dependencies**: Sets up the build environment ([.github/workflows/publish.yml:21-22]()).
2.  **Build package & docs**: Creates wheel and source distributions via `scripts/build` ([.github/workflows/publish.yml:23-24]()).
3.  **Publish to PyPI & deploy docs**: Runs `scripts/publish` ([.github/workflows/publish.yml:25-26]()).

The publish script uses Twine with token-based authentication ([.github/workflows/publish.yml:27-29]()):
*   `TWINE_USERNAME`: Set to `__token__`.
*   `TWINE_PASSWORD`: Populated from GitHub secret `PYPI_TOKEN`.

**Sources:** [.github/workflows/publish.yml:13-29]()

## Automated Release Process

The `scripts/publish` script contains the logic for final verification and deployment.

### Version Verification

Before uploading, the script performs a safety check to ensure the git tag matches the version defined in the codebase ([scripts/publish:15-20]()):

1.  It extracts the version from `httpx/__version__.py` ([scripts/publish:15]()).
2.  It compares `refs/tags/${VERSION}` against the `GITHUB_REF` environment variable ([scripts/publish:17]()).
3.  If they do not match, the process exits with an error ([scripts/publish:19]()).

### Deployment Actions

Once verified, the script performs two primary actions:
1.  **PyPI Upload**: Executes `twine upload dist/*` ([scripts/publish:25]()).
2.  **Documentation Deployment**: Executes `mkdocs gh-deploy --force` to update the GitHub Pages site ([scripts/publish:26]()).

**Sources:** [scripts/publish:1-27]()

## Build System Integration

The `scripts/build` script prepares the artifacts used by both the test and publish workflows.

**Diagram: Build Artifact Generation**
```mermaid
graph LR
    subgraph "scripts/build"
        B["python -m build"]
        C["twine check dist/*"]
        D["mkdocs build"]
    end
    
    B --> Dist["dist/ directory<br/>.whl & .tar.gz"]
    Dist --> C
    D --> Site["site/ directory<br/>Static HTML"]
```

1.  **Package Building**: Uses the `build` module to generate PEP 517 compliant distributions ([scripts/build:11]()).
2.  **Distribution Check**: Uses `twine check` to ensure the generated packages are valid for PyPI ([scripts/build:12]()).
3.  **Documentation Build**: Uses `mkdocs build` to generate the static documentation site ([scripts/build:13]()).

**Sources:** [scripts/build:1-14]()

## Summary of CI/CD Flow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant GH as GitHub Actions
    participant Scripts as Shell Scripts
    participant PyPI as PyPI Registry
    
    Dev->>GH: Push Tag (e.g. 0.27.0)
    GH->>Scripts: scripts/install
    GH->>Scripts: scripts/build
    Scripts->>Scripts: python -m build
    Scripts->>Scripts: twine check dist/*
    GH->>Scripts: scripts/publish
    Scripts->>Scripts: Verify Tag == __version__.py
    Scripts->>PyPI: twine upload dist/*
    Scripts->>GH: mkdocs gh-deploy
```

**Sources:** [.github/workflows/publish.yml:1-30](), [scripts/publish:1-27](), [scripts/build:1-14]()

---

# Page: Documentation

# Documentation

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [docs/advanced/extensions.md](docs/advanced/extensions.md)
- [docs/api.md](docs/api.md)
- [docs/exceptions.md](docs/exceptions.md)
- [docs/img/speakeasy.png](docs/img/speakeasy.png)
- [docs/overrides/partials/nav.html](docs/overrides/partials/nav.html)
- [mkdocs.yml](mkdocs.yml)
- [scripts/docs](scripts/docs)

</details>



## Purpose and Scope

This page describes the documentation system for the `httpx` library. The system is designed to provide high-quality, searchable, and automatically synchronized technical documentation. It utilizes `MkDocs` as the static site generator, the `mkdocs-material` theme for its user interface, and `mkautodoc` to generate API references directly from the source code docstrings.

## Documentation Stack Overview

The `httpx` documentation system integrates Markdown-based guides with automated API introspection.

```mermaid
graph TB
    subgraph "Documentation Sources"
        DocsDir["docs/*.md<br/>Markdown Guides"]
        SourceCode["httpx/*.py<br/>Python Docstrings"]
        MkDocsYaml["mkdocs.yml<br/>Main Configuration"]
    end
    
    subgraph "Build Tools"
        MkDocs["MkDocs<br/>Static Site Generator"]
        MkAutodoc["mkautodoc<br/>API Doc Plugin"]
        Material["mkdocs-material<br/>Theme Engine"]
    end
    
    subgraph "Build Process"
        Parse["Parse Markdown<br/>and Docstrings"]
        Generate["Generate HTML<br/>Pages"]
        Theme["Apply Material<br/>Styling & Overrides"]
    end
    
    subgraph "Output"
        SiteDir["site/<br/>Generated HTML"]
        LiveSite["www.python-httpx.org"]
    end
    
    DocsDir --> MkDocs
    SourceCode --> MkAutodoc
    MkDocsYaml --> MkDocs
    
    MkDocs --> Parse
    MkAutodoc --> Parse
    Material --> Theme
    
    Parse --> Generate
    Generate --> Theme
    Theme --> SiteDir
    SiteDir --> LiveSite
```

**Documentation Build Pipeline**: Markdown sources and Python docstrings are processed by `MkDocs` with the `mkautodoc` plugin, styled with the Material theme, and output as static HTML.

Sources: [mkdocs.yml:1-62](), [scripts/docs:1-10]()

## MkDocs Configuration

The documentation system is configured via `mkdocs.yml` [mkdocs.yml:1-62](). This file defines the site metadata, navigation structure, and the technical extensions used to render the documentation.

### Site Metadata and Theme
The project uses the `material` theme [mkdocs.yml:6-6](), which is customized with a dark/light mode toggle [mkdocs.yml:8-19](). The configuration points to a custom directory for overrides at `docs/overrides` [mkdocs.yml:7-7](), allowing for tailored HTML components like the navigation sidebar [docs/overrides/partials/nav.html:1-53]().

### Navigation Structure
The `nav` section [mkdocs.yml:25-52]() organizes the documentation into five primary categories:
1. **Introduction**: High-level overview.
2. **QuickStart**: Basic usage patterns.
3. **Advanced**: Deep dives into specific features like `Transports`, `Proxies`, and `Event Hooks`.
4. **Guides**: Conceptual guides for `Async`, `HTTP/2`, and `Compatibility`.
5. **API Reference**: Detailed technical specifications for classes and exceptions.

Sources: [mkdocs.yml:25-52](), [docs/overrides/partials/nav.html:1-53]()

## API Documentation Generation

`httpx` uses the `mkautodoc` extension [mkdocs.yml:58-58]() to bridge the gap between "Natural Language Space" (Markdown) and "Code Entity Space" (Python source).

### The mkautodoc Mechanism
The `mkautodoc` plugin introspects the `httpx` package to extract docstrings and signatures. This is primarily used in `docs/api.md` and `docs/exceptions.md`.

```mermaid
graph LR
    subgraph "Code Entity Space"
        ClientClass["httpx.Client"]
        AsyncClientClass["httpx.AsyncClient"]
        HTTPErrorClass["httpx.HTTPError"]
    end
    
    subgraph "Markdown Space (docs/api.md)"
        ClientDirective["::: httpx.Client<br/>:members: ..."]
        AsyncDirective["::: httpx.AsyncClient<br/>:members: ..."]
    end

    subgraph "Markdown Space (docs/exceptions.md)"
        ErrorDirective["::: httpx.HTTPError<br/>:docstring:"]
    end
    
    ClientClass -- "Introspected by mkautodoc" --> ClientDirective
    AsyncClientClass -- "Introspected by mkautodoc" --> AsyncDirective
    HTTPErrorClass -- "Introspected by mkautodoc" --> ErrorDirective
```

**API Introspection Map**: Associations between core library classes and their corresponding documentation directives.

### Documented Members
The `api.md` file explicitly defines which members of the `Client` and `AsyncClient` should be exposed in the documentation [docs/api.md:40-48]().

| Code Entity | Documented Members |
| :--- | :--- |
| `httpx.Client` | `headers`, `cookies`, `params`, `auth`, `request`, `get`, `head`, `options`, `post`, `put`, `patch`, `delete`, `stream`, `build_request`, `send`, `close` [docs/api.md:42-42]() |
| `httpx.AsyncClient` | Same as `Client`, plus `aclose` [docs/api.md:48-48]() |

Sources: [docs/api.md:11-48](), [mkdocs.yml:58-58]()

## Exception Hierarchy Documentation

The documentation includes a comprehensive guide to the exception hierarchy, which is crucial for robust error handling. The `docs/exceptions.md` file uses a combination of manual Markdown lists to show the inheritance tree and `mkautodoc` directives for detailed class descriptions [docs/exceptions.md:9-36]().

```mermaid
graph TD
    subgraph "Exception Code Entities"
        HTTPError["httpx.HTTPError"]
        RequestError["httpx.RequestError"]
        TransportError["httpx.TransportError"]
        TimeoutException["httpx.TimeoutException"]
        NetworkError["httpx.NetworkError"]
    end

    HTTPError --> RequestError
    RequestError --> TransportError
    TransportError --> TimeoutException
    TransportError --> NetworkError
    
    subgraph "Specific Timeouts"
        ConnectTimeout["httpx.ConnectTimeout"]
        ReadTimeout["httpx.ReadTimeout"]
    end
    
    TimeoutException --> ConnectTimeout
    TimeoutException --> ReadTimeout
```

**Exception Inheritance Structure**: Visual representation of the core exception classes documented in `docs/exceptions.md`.

Sources: [docs/exceptions.md:7-36](), [docs/exceptions.md:42-124]()

## Development and Build Scripts

To maintain the documentation, the repository provides a shell script for local serving.

### Documentation Server Script
The script located at `scripts/docs` automates the process of starting the `MkDocs` development server.

1. **Environment Detection**: It checks for a local virtual environment (`venv`) to set the correct execution prefix [scripts/docs:4-6]().
2. **Execution**: It runs `mkdocs serve` [scripts/docs:10-10](), which provides:
    - A local web server (usually at `localhost:8000`).
    - Live-reloading when Markdown files or source code docstrings are modified.

Sources: [scripts/docs:1-10]()

---

# Page: Glossary

# Glossary

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [CHANGELOG.md](CHANGELOG.md)
- [httpx/__init__.py](httpx/__init__.py)
- [httpx/__version__.py](httpx/__version__.py)
- [httpx/_client.py](httpx/_client.py)
- [httpx/_exceptions.py](httpx/_exceptions.py)
- [httpx/_models.py](httpx/_models.py)
- [httpx/_transports/default.py](httpx/_transports/default.py)
- [httpx/_urlparse.py](httpx/_urlparse.py)
- [httpx/_urls.py](httpx/_urls.py)
- [httpx/_utils.py](httpx/_utils.py)
- [pyproject.toml](pyproject.toml)
- [requirements.txt](requirements.txt)
- [tests/client/test_proxies.py](tests/client/test_proxies.py)
- [tests/models/test_url.py](tests/models/test_url.py)
- [tests/test_utils.py](tests/test_utils.py)

</details>



This page defines codebase-specific terms, jargon, and domain concepts used within the `httpx` project. It serves as a technical reference for engineers to understand the internal mapping between high-level HTTP concepts and their specific implementations in the code.

## Core Concepts

### Client State
The lifecycle of a `Client` or `AsyncClient` instance is managed via an internal state machine.
*   **UNOPENED**: The client is instantiated but has not sent requests or entered a context manager [httpx/_client.py:126-129]().
*   **OPENED**: The client is active, either within a `with` block or after the first request [httpx/_client.py:130-132]().
*   **CLOSED**: The client has been explicitly closed or exited its context, releasing resources like connection pools [httpx/_client.py:133-137]().

### Transport
A pluggable layer that handles the actual network I/O or application-level dispatch.
*   **HTTPTransport**: The default synchronous transport that uses `httpcore` for network requests [httpx/_transports/default.py:135-150]().
*   **ASGITransport / WSGITransport**: Specialized transports that call into Python web applications directly without a network stack [httpx/__init__.py:33,99]().
*   **MockTransport**: A transport used for testing that returns hardcoded responses [httpx/__init__.py:64]().

### ByteStream
An abstraction for the body of a request or response. `httpx` distinguishes between sync and async streams to support different concurrency models.
*   **SyncByteStream**: Interface for synchronous body iteration [httpx/_types.py:45]().
*   **AsyncByteStream**: Interface for asynchronous body iteration using `__aiter__` [httpx/_types.py:34]().
*   **BoundSyncStream / BoundAsyncStream**: Wrappers that link a stream to a `Response` object to calculate `response.elapsed` timing upon closure [httpx/_client.py:139-183]().

---

## Technical Jargon & Abbreviations

| Term | Definition | Code Reference |
| :--- | :--- | :--- |
| **UDS** | Unix Domain Socket. A data communications endpoint for exchanging data between processes executing on the same host. | [httpx/_transports/default.py:145]() |
| **H2** | Shorthand for HTTP/2 protocol support. | [pyproject.toml:48-50]() |
| **Netloc** | The network location part of a URL, including host and port (e.g., `example.com:8080`). | [httpx/_urls.py]() |
| **Userinfo** | The `username:password` portion of a URL. | [httpx/_models.py:209]() |
| **Mounts** | A dictionary mapping URL patterns to specific transport instances for granular routing. | [httpx/_client.py:49,81]() |
| **Event Hook** | A callback function executed during the request/response lifecycle. | [httpx/_client.py:185]() |

---

## System Mapping Diagrams

### Request Lifecycle Entities
The following diagram maps high-level request phases to the internal classes and functions that handle them.

**Request Flow Mapping**
```mermaid
graph TD
    subgraph "Natural Language Space"
        A["User Request"]
        B["Connection Pooling"]
        C["Network I/O"]
        D["Error Mapping"]
    end

    subgraph "Code Entity Space"
        A --> E["httpx.Client.request()"]
        E --> F["httpx.Request"]
        F --> G["httpx.HTTPTransport"]
        G --> H["httpcore.ConnectionPool"]
        H --> I["map_httpcore_exceptions()"]
    end

    E -- "uses" --> F
    G -- "wraps" --> H
    I -- "transforms" --> J["httpx.RequestError"]
```
Sources: [httpx/_client.py:600-620](), [httpx/_transports/default.py:135-167](), [httpx/_transports/default.py:96-119]()

### URL Structure and Parsing
`httpx` implements its own URL parsing logic to ensure strict compliance and efficient manipulation.

**URL Component Mapping**
```mermaid
graph LR
    subgraph "URL Components"
        S["Scheme"]
        H["Host"]
        P["Port"]
        PA["Path"]
        Q["Query"]
    end

    subgraph "httpx.URL Class Entities"
        S --> S1["self.scheme"]
        H --> H1["self.host"]
        P --> P1["self.port"]
        PA --> PA1["self.path"]
        Q --> Q1["self.params (QueryParams)"]
    end

    URL_STR["'https://user:pass@example.com:443/api?v=1'"] -- "Parsed by" --> URL_OBJ["httpx.URL"]
    URL_OBJ -- "provides" --> S1
    URL_OBJ -- "provides" --> H1
```
Sources: [httpx/_urls.py](), [tests/models/test_url.py:8-38](), [httpx/_models.py:139-150]()

---

## Internal Utility Functions

### `map_httpcore_exceptions`
A context manager used within transports to catch low-level `httpcore` exceptions and re-raise them as their `httpx` equivalents (e.g., mapping `httpcore.ReadTimeout` to `httpx.ReadTimeout`).
*   **Location**: [httpx/_transports/default.py:96-119]()
*   **Mechanism**: Uses a global `HTTPCORE_EXC_MAP` dictionary [httpx/_transports/default.py:71]().

### `get_environment_proxies`
Detects proxy settings from system environment variables (`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY`).
*   **Location**: [httpx/_utils.py:30-76]()
*   **Logic**: Parses the `NO_PROXY` string into `URLPattern` objects for exclusion matching [httpx/_utils.py:47-74]().

### `USE_CLIENT_DEFAULT`
A sentinel object used to distinguish between a parameter being explicitly set to `None` versus being left at its default value (which should then be inherited from the `Client` configuration).
*   **Location**: [httpx/_client.py:94-114]()

---
Sources:
- [httpx/_client.py:94-137]()
- [httpx/_client.py:139-183]()
- [httpx/_transports/default.py:71-119]()
- [httpx/_transports/default.py:135-187]()
- [httpx/_utils.py:30-76]()
- [httpx/_models.py:139-150]()
- [httpx/_types.py:34-46]()
- [pyproject.toml:48-56]()
- [httpx/__init__.py:29-100]()
