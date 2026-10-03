# Page: Overview

# Overview

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [HISTORY.md](HISTORY.md)
- [MANIFEST.in](MANIFEST.in)
- [README.md](README.md)
- [docs/api.rst](docs/api.rst)
- [docs/community/faq.rst](docs/community/faq.rst)
- [docs/index.rst](docs/index.rst)
- [docs/user/advanced.rst](docs/user/advanced.rst)
- [docs/user/quickstart.rst](docs/user/quickstart.rst)
- [src/requests/__init__.py](src/requests/__init__.py)
- [src/requests/__version__.py](src/requests/__version__.py)

</details>



This page provides a high-level introduction to the Requests library: its purpose, design philosophy, core components, and how they fit together. For detailed information about specific subsystems, see [Architecture](#1.1), [Main Components](#1.2), and [Core API](#2).

## Purpose and Scope

Requests is a Python HTTP client library designed to make HTTP requests simple and intuitive. It provides a high-level, user-friendly interface for sending HTTP/1.1 requests while handling complex protocol details internally. The library is built on top of `urllib3` for low-level HTTP operations and is widely considered the definitive HTTP library for Python. [docs/index.rst:53-56]()

Sources: [README.md:9-24](), [docs/index.rst:6-32]()

## What is Requests?

Requests is an open-source HTTP library for Python that provides:

- **User-Friendly API**: Simple function calls like `requests.get()` and `requests.post()` for common HTTP operations. [README.md:11-24](), [src/requests/api.py:64-158]()
- **Persistent Sessions**: The `Session` class for maintaining state across multiple requests, including cookies and connection pooling. [README.md:46](), [src/requests/sessions.py:358-376]()
- **Automatic Protocol Handling**: Connection pooling, keep-alive, redirects, and encoding detection without manual configuration. [docs/index.rst:53-56](), [src/requests/sessions.py:164-297]()
- **Production-Ready**: Pulling in around 300M downloads per week and depended upon by over 4,000,000 repositories. [README.md:28]()

The library officially supports Python 3.10+ and runs on PyPy. [README.md:38](), [docs/index.rst:79]()

Sources: [README.md:1-38](), [docs/index.rst:6-79](), [src/requests/__init__.py:72-97]()

## Design Philosophy: HTTP for Humans™

The library follows the principle of "HTTP for Humans™" — making HTTP operations as simple and intuitive as possible while maintaining power and flexibility for advanced use cases. [docs/index.rst:6-32](), [src/requests/__version__.py:6]()

**Core Principles:**

| Principle | Implementation |
|-----------|----------------|
| **Simplicity** | No manual query string building or form encoding required. [README.md:26-27]() |
| **Automatic Handling** | Connection pooling and content decoding happen automatically via `urllib3`. [docs/index.rst:55-56](), [docs/community/faq.rst:11-12]() |
| **Python-Native** | Uses native types like `dict` for headers and cookies, and provides a `.json()` method. [README.md:22-23](), [README.md:49](), [src/requests/models.py:932-972]() |
| **Safety by Default** | Browser-style TLS/SSL verification is standard. [README.md:47]() |
| **Extensibility** | Supports custom authentication and Transport Adapters. [README.md:48-52](), [src/requests/adapters.py:97-106]() |

```python
# Example demonstrating simplicity
import requests
r = requests.get('https://api.github.com/user', auth=('user', 'pass'))
r.status_code  # 200
r.json()       # Automatically parsed JSON response
```

Sources: [README.md:9-27](), [docs/index.rst:32-57](), [docs/community/faq.rst:11-19](), [src/requests/models.py:932-972]()

## System Overview

The following diagram shows the major subsystems and how they relate to each other:

**Bridge: System Concepts to Code Entities**

| System Name | Code Entity |
|-------------|-------------|
| **Public API** | `requests.api` [src/requests/api.py:14-20]() |
| **Session Manager** | `requests.sessions.Session` [src/requests/sessions.py:358-376]() |
| **Request Model** | `requests.models.Request` [src/requests/models.py:206-224]() |
| **Prepared Request** | `requests.models.PreparedRequest` [src/requests/models.py:313-329]() |
| **Response Model** | `requests.models.Response` [src/requests/models.py:616-635]() |
| **Transport Adapter** | `requests.adapters.HTTPAdapter` [src/requests/adapters.py:97-106]() |

```mermaid
graph TB
    subgraph "UserInterface"
        API["requests.api<br/>get(), post(), etc."]
        Session["requests.sessions.Session<br/>Persistent state"]
    end
    
    subgraph "RequestResponseLayer"
        Request["requests.models.Request<br/>User-facing model"]
        PreparedRequest["requests.models.PreparedRequest<br/>Wire-ready object"]
        Response["requests.models.Response<br/>Server response"]
    end
    
    subgraph "TransportLayer"
        HTTPAdapter["requests.adapters.HTTPAdapter<br/>urllib3 interface"]
        Pools["ConnectionPools<br/>urllib3.PoolManager"]
    end
    
    subgraph "SupportingSystems"
        Utils["requests.utils<br/>Helpers"]
        Auth["requests.auth<br/>AuthBase"]
        Exceptions["requests.exceptions<br/>Hierarchy"]
        Structures["requests.structures<br/>CaseInsensitiveDict"]
    end
    
    subgraph "ExternalDependencies"
        urllib3["urllib3"]
        certifi["certifi"]
        charset["charset_normalizer"]
        idna["idna"]
    end
    
    API --> Session
    API --> Request
    Session --> Request
    Request --> PreparedRequest
    Session --> HTTPAdapter
    PreparedRequest --> HTTPAdapter
    HTTPAdapter --> Response
    HTTPAdapter --> Pools
    HTTPAdapter --> urllib3
    
    Session --> Auth
    Session --> Structures
    PreparedRequest --> Utils
    Response --> Utils
    Utils --> charset
    Utils --> idna
    
    Response --> Exceptions
    HTTPAdapter --> Exceptions
```

Sources: [README.md:40-57](), [docs/index.rst:53-77](), [src/requests/sessions.py:650-785](), [src/requests/adapters.py:438-557]()

## Request Lifecycle

This diagram illustrates how a request flows through the system from user code to server response:

```mermaid
sequenceDiagram
    participant User
    participant api["requests.api"]
    participant Session["requests.sessions.Session"]
    participant PrepReq["requests.models.PreparedRequest"]
    participant Adapter["requests.adapters.HTTPAdapter"]
    participant urllib3["urllib3.PoolManager"]
    participant Server
    
    User->>api: requests.get(url, auth)
    api->>Session: Create temporary Session()
    Session->>PrepReq: prepare_request(Request)
    Note over PrepReq: Merge session cookies,<br/>headers, and auth
    
    Session->>Adapter: send(PreparedRequest)
    Note over Adapter: Select connection from pool
    Adapter->>urllib3: urlopen()
    urllib3->>Server: HTTP request
    Server-->>urllib3: HTTP response
    urllib3-->>Adapter: urllib3.HTTPResponse
    
    Adapter->>Adapter: Build requests.Response
    Adapter-->>Session: requests.Response
    Session-->>api: requests.Response
    api-->>User: requests.Response
```

Sources: [README.md:11-24](), [docs/index.rst:36-57](), [src/requests/sessions.py:483-500](), [src/requests/sessions.py:650-700](), [src/requests/adapters.py:438-500]()

## Key Features

The library provides comprehensive HTTP functionality:

### Network Protocol Features
- **Keep-Alive & Connection Pooling**: Automatic connection reuse via `urllib3`. [docs/index.rst:55-56](), [docs/user/advanced.rst:15-18]()
- **Chunked Transfer Encoding**: Support for streaming large request and response bodies. [README.md:56]()
- **Streaming Downloads**: Process large responses incrementally via `stream=True`. [README.md:54](), [docs/user/quickstart.rst:170-194]()

### Authentication & Security
- **TLS/SSL Verification**: Browser-style certificate verification. [README.md:47]()
- **HTTP Authentication**: Built-in support for Basic and Digest authentication. [README.md:48](), [src/requests/auth.py:76-105]()
- **Automatic .netrc Support**: Honors credentials stored in `.netrc` files. [README.md:55](), [src/requests/utils.py:210-245]()

### Data Handling
- **Automatic Content Decoding**: Transparent decompression of gzip, deflate, and brotli (if installed). [docs/community/faq.rst:11-15](), [docs/user/quickstart.rst:129-133]()
- **JSON Support**: Native `.json()` method for response bodies. [README.md:22-23](), [src/requests/models.py:932-972]()
- **International Domains**: Full IDNA support for internationalized domain names. [README.md:45](), [src/requests/models.py:389-405]()

Sources: [README.md:40-57](), [docs/index.rst:58-77](), [docs/community/faq.rst:8-19](), [src/requests/models.py:932-972]()

## Version and Support

**Python Version Support**: 
- **Minimum**: Python 3.10+ [README.md:38](), [src/requests/__init__.py:72-79]()
- **Legacy**: Python 2.7 support was dropped in version 2.28.0. [docs/community/faq.rst:64-67]()

Sources: [README.md:30-38](), [docs/community/faq.rst:55-70](), [src/requests/__version__.py:8]()

## Related Documentation

For more detailed information about specific aspects of the library:

- **System Architecture**: See [Architecture](#1.1) for detailed layer descriptions.
- **Component Details**: See [Main Components](#1.2) for in-depth coverage of core classes.
- **API Reference**: See [Core API](#2) for detailed function and method documentation.
- **Authentication**: See [Authentication](#3) for auth mechanisms.
- **Advanced Usage**: See [Advanced Usage](#4) for SSL, proxies, and hooks.
- **Development**: See [Development Guide](#7) for contributing and build instructions.

Sources: [docs/index.rst:82-144]()

---

# Page: Architecture

# Architecture

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [README.md](README.md)
- [docs/api.rst](docs/api.rst)
- [docs/community/faq.rst](docs/community/faq.rst)
- [docs/index.rst](docs/index.rst)
- [docs/user/advanced.rst](docs/user/advanced.rst)
- [docs/user/quickstart.rst](docs/user/quickstart.rst)
- [src/requests/_types.py](src/requests/_types.py)
- [src/requests/adapters.py](src/requests/adapters.py)
- [src/requests/sessions.py](src/requests/sessions.py)
- [tests/test_adapters.py](tests/test_adapters.py)

</details>



This page describes the high-level architecture of the Requests library, including its layered design, component organization, and key architectural patterns. It explains how the library transforms user-level HTTP requests into network operations through a series of well-defined layers.

## Layered Architecture

The Requests library follows a layered architecture that separates concerns from high-level user interaction down to low-level HTTP transport:

Title: Requests Layered Architecture
```mermaid
graph TB
    subgraph Layer1["User API Layer"]
        api["requests.api module<br/>get(), post(), put(), delete(), etc."]
        session_factory["Session() factory"]
    end
    
    subgraph Layer2["Session Layer"]
        Session["Session class<br/>Persistent state and configuration"]
        merge["merge_setting()"]
        prepare["prepare_request()"]
    end
    
    subgraph Layer3["Request/Response Model Layer"]
        Request["Request class<br/>User-created request"]
        PreparedRequest["PreparedRequest class<br/>Prepared for transmission"]
        Response["Response class<br/>Server response"]
    end
    
    subgraph Layer4["Transport Adapter Layer"]
        BaseAdapter["BaseAdapter base class"]
        HTTPAdapter["HTTPAdapter implementation"]
    end
    
    subgraph Layer5["Connection Pool Layer"]
        PoolManager["urllib3.poolmanager.PoolManager"]
        ProxyManager["urllib3.poolmanager.proxy_from_url"]
    end
    
    subgraph Layer6["External Dependencies"]
        urllib3["urllib3 library<br/>Low-level HTTP"]
        certifi["certifi<br/>CA certificates"]
        charset["charset_normalizer<br/>Encoding detection"]
        idna["idna library<br/>Domain encoding"]
    end
    
    api --> Session
    session_factory --> Session
    Session --> prepare
    Session --> merge
    prepare --> Request
    Request --> PreparedRequest
    Session --> HTTPAdapter
    PreparedRequest --> HTTPAdapter
    HTTPAdapter --> Response
    
    BaseAdapter -.->|"implements"| HTTPAdapter
    HTTPAdapter --> PoolManager
    HTTPAdapter --> ProxyManager
    
    PoolManager --> urllib3
    ProxyManager --> urllib3
    HTTPAdapter --> certifi
    Response --> charset
    PreparedRequest --> idna
```

**Sources:** [docs/api.rst:13-27](), [src/requests/sessions.py:488-812](), [src/requests/models.py:232-640](), [src/requests/adapters.py:158-699](), [src/requests/adapters.py:31-34]()

## Component Organization

The library's components are organized into modules with specific responsibilities:

| Module | Primary Components | Purpose |
|--------|-------------------|---------|
| `requests.api` | `get()`, `post()`, `put()`, `delete()`, `head()`, `options()`, `patch()`, `request()` | Convenience functions that create temporary sessions [docs/api.rst:19-27]() |
| `requests.sessions` | `Session`, `SessionRedirectMixin` | Persistent connection management and state [src/requests/sessions.py:127-812]() |
| `requests.models` | `Request`, `PreparedRequest`, `Response` | Core data models for HTTP transactions [docs/api.rst:53-66]() |
| `requests.adapters` | `BaseAdapter`, `HTTPAdapter` | Transport layer abstraction and urllib3 interface [src/requests/adapters.py:122-699]() |
| `requests.auth` | `AuthBase`, `HTTPBasicAuth`, `HTTPDigestAuth` | Authentication handlers [docs/api.rst:76-79]() |
| `requests.exceptions` | `RequestException` hierarchy | Error handling [docs/api.rst:31-38]() |
| `requests.utils` | Various utility functions | URL parsing, encoding, proxy resolution [docs/api.rst:86-98]() |
| `requests.cookies` | `RequestsCookieJar` | Cookie management [docs/api.rst:91-105]() |

## Request Lifecycle Architecture

The following diagram shows how a request flows through the system from user invocation to receiving a response:

Title: Request Lifecycle Flow
```mermaid
sequenceDiagram
    participant User
    participant api as "requests.api"
    participant Session as "Session instance"
    participant Request as "Request object"
    participant PreparedRequest as "PreparedRequest object"
    participant HTTPAdapter as "HTTPAdapter instance"
    participant PoolManager as "urllib3.PoolManager"
    participant Server as "HTTP Server"
    
    User->>api: requests.get(url, params, headers, ...)
    api->>Session: Create Session()
    api->>Session: request(method='GET', url, ...)
    Session->>Request: Create Request(method, url, ...)
    Session->>Session: prepare_request(req)
    Session->>PreparedRequest: req.prepare()
    
    Note over PreparedRequest: prepare_method()<br/>prepare_url()<br/>prepare_headers()<br/>prepare_cookies()<br/>prepare_body()<br/>prepare_auth()
    
    Session->>Session: merge_environment_settings()
    Session->>HTTPAdapter: get_adapter(url)
    Session->>HTTPAdapter: send(prep_req, timeout, verify, cert, proxies)
    
    HTTPAdapter->>PoolManager: urlopen(method, url, body, headers, ...)
    
    PoolManager->>Server: HTTP Request
    Server-->>PoolManager: HTTP Response
    
    PoolManager-->>HTTPAdapter: urllib3.response.HTTPResponse
    HTTPAdapter->>HTTPAdapter: build_response(req, resp)
    HTTPAdapter-->>Session: Response object
    Session-->>api: Response object
    api-->>User: Response object
```

**Sources:** [docs/user/advanced.rst:85-118](), [src/requests/sessions.py:488-645](), [src/requests/models.py:353-379](), [src/requests/adapters.py:475-699]()

## Adapter Pattern and Connection Management

The library uses the Adapter pattern to abstract the transport layer, allowing for different HTTP implementations and custom connection behavior:

Title: Adapter and Connection Pool Architecture
```mermaid
graph TB
    subgraph Session["Session State"]
        session_adapters["adapters: OrderedDict<br/>URL prefix -> Adapter"]
        default_http["'http://' -> HTTPAdapter"]
        default_https["'https://' -> HTTPAdapter"]
    end
    
    subgraph HTTPAdapter["HTTPAdapter Instance"]
        poolmanager["poolmanager: PoolManager"]
        proxy_manager_dict["proxy_manager: dict"]
        max_retries["max_retries: Retry"]
    end
    
    subgraph PoolManager["urllib3.poolmanager.PoolManager"]
        pools["pools: RecentlyUsedContainer"]
    end
    
    subgraph ConnectionPools["urllib3 Connection Pools"]
        pool1["HTTPConnectionPool<br/>(host1, port)"]
        pool2["HTTPSConnectionPool<br/>(host2, port)"]
    end
    
    session_adapters --> default_http
    session_adapters --> default_https
    
    default_http --> poolmanager
    default_https --> poolmanager
    
    poolmanager --> pools
    pools --> pool1
    pools --> pool2
```

The `HTTPAdapter` manages the lifecycle of connection pools through `urllib3`. Separate pools are maintained for different hosts and schemes to facilitate connection reuse via HTTP Keep-Alive [docs/user/advanced.rst:10-18]().

**Sources:** [src/requests/adapters.py:158-243](), [src/requests/sessions.py:488-530](), [docs/user/advanced.rst:10-18]()

## Preparation Pipeline

The transformation from a user's `Request` to a `PreparedRequest` ready for transmission follows a specific pipeline:

Title: PreparedRequest Preparation Pipeline
```mermaid
graph LR
    Request["Request<br/>User input"]
    
    subgraph PreparePhase["PreparedRequest.prepare() Pipeline"]
        prepare_method["prepare_method()"]
        prepare_url["prepare_url()"]
        prepare_headers["prepare_headers()"]
        prepare_cookies["prepare_cookies()"]
        prepare_body["prepare_body()"]
        prepare_auth["prepare_auth()"]
        prepare_hooks["prepare_hooks()"]
    end
    
    PreparedRequest["PreparedRequest<br/>Ready for transmission"]
    
    Request --> prepare_method
    prepare_method --> prepare_url
    prepare_url --> prepare_headers
    prepare_headers --> prepare_cookies
    prepare_cookies --> prepare_body
    prepare_body --> prepare_auth
    prepare_auth --> prepare_hooks
    prepare_hooks --> PreparedRequest
```

Each preparation step modifies specific attributes of the `PreparedRequest` object. This process ensures that high-level Python types (like dictionaries for parameters or cookies) are converted into the string and byte formats required by the HTTP protocol [docs/user/advanced.rst:119-149]().

**Sources:** [src/requests/models.py:353-379](), [src/requests/models.py:395-640]()

## Key Architectural Patterns

### 1. Adapter Pattern for Transport Abstraction
The `BaseAdapter` interface allows swapping HTTP implementations. The default `HTTPAdapter` wraps `urllib3`, but users can mount custom adapters for specific URL prefixes via `Session.mount()` [src/requests/sessions.py:804-812]().

### 2. Mixin Classes for Functionality Composition
The library uses mixins to compose functionality:
- `SessionRedirectMixin`: Encapsulates complex HTTP redirect logic, including header re-encoding and security checks like `should_strip_auth` [src/requests/sessions.py:127-310]().

### 3. Immutable Preparation
`Request` objects represent user intent, while `PreparedRequest` objects represent the actual bytes sent over the wire. This separation allows users to inspect or modify a request after it has been fully resolved (e.g., after merging Session-level cookies and headers) but before it is sent [docs/user/advanced.rst:119-149]().

### 4. Hook System
A simple callback system allows users to inject logic at specific points. Currently, the `response` hook is the primary extension point, executed immediately after a response is generated by an adapter [src/requests/sessions.py:36-37](), [src/requests/_types.py:43-44]().

### 5. Environment Settings Merge Strategy
The `Session` merges settings from three sources in order of precedence:
1. Method-level arguments (e.g., `requests.get(..., timeout=5)`)
2. Session-level attributes (e.g., `session.timeout = 10`)
3. Environment variables (e.g., `HTTP_PROXY`, `REQUESTS_CA_BUNDLE`) [src/requests/sessions.py:76-105]().

## Dependency Architecture

The library relies on a small set of focused dependencies to handle low-level networking and data standards:

Title: Requests Dependency Architecture
```mermaid
graph TB
    requests["requests library"]
    
    subgraph CoreDeps["Core Dependencies"]
        urllib3["urllib3<br/>Connection pooling & HTTP/1.1"]
        certifi["certifi<br/>CA Bundle"]
        idna_lib["idna<br/>Domain encoding"]
    end
    
    subgraph Detection["Encoding Detection"]
        charset["charset_normalizer / chardet"]
    end
    
    requests --> urllib3
    requests --> certifi
    requests --> idna_lib
    requests --> Detection
```

**Sources:** [README.md:40-57](), [src/requests/adapters.py:17-34](), [docs/api.rst:86-89]()

---

# Page: Main Components

# Main Components

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [AUTHORS.rst](AUTHORS.rst)
- [src/requests/__init__.py](src/requests/__init__.py)
- [src/requests/api.py](src/requests/api.py)
- [src/requests/models.py](src/requests/models.py)
- [tests/test_requests.py](tests/test_requests.py)

</details>



This page provides an overview of the primary components in the Requests library and how they interact to process HTTP requests. For detailed information about the overall architecture, see [Architecture](#1.1). For specific usage patterns of these components, see [Core API](#2).

The Requests library is built around several key components that work together to provide a user-friendly HTTP client interface. These components are organized in layers, from high-level user-facing objects down to low-level transport mechanisms.

## Component Overview

The following diagram shows the main components and their relationships:

```mermaid
graph TB
    subgraph "User-Facing Objects"
        Request["Request<br/>(models.py)"]
        PreparedRequest["PreparedRequest<br/>(models.py)"]
        Response["Response<br/>(models.py)"]
    end
    
    subgraph "Session Layer"
        Session["Session<br/>(sessions.py)"]
    end
    
    subgraph "Transport Layer"
        BaseAdapter["BaseAdapter<br/>(adapters.py)"]
        HTTPAdapter["HTTPAdapter<br/>(adapters.py)"]
    end
    
    subgraph "Supporting Infrastructure"
        Auth["AuthBase<br/>HTTPBasicAuth<br/>HTTPDigestAuth<br/>(auth.py)"]
        Structures["CaseInsensitiveDict<br/>LookupDict<br/>(structures.py)"]
        Utils["utils module<br/>(utils.py)"]
        Exceptions["RequestException<br/>HTTPError<br/>ConnectionError<br/>(exceptions.py)"]
    end
    
    Request -->|"prepare()"| PreparedRequest
    Session -->|"manages"| Request
    Session -->|"sends via"| HTTPAdapter
    PreparedRequest -->|"sent by"| HTTPAdapter
    HTTPAdapter -->|"builds"| Response
    HTTPAdapter -.->|"inherits"| BaseAdapter
    
    Session -->|"uses"| Auth
    Session -->|"uses"| Structures
    PreparedRequest -->|"uses"| Utils
    Response -->|"uses"| Structures
    HTTPAdapter -->|"raises"| Exceptions
```

**Sources:** [src/requests/models.py:1-6](), [src/requests/sessions.py:1-7](), [src/requests/adapters.py:1-10]()

## Request and PreparedRequest

The `Request` and `PreparedRequest` classes represent HTTP requests at different stages of preparation.

### Request Class

The `Request` class is a user-created object that contains the high-level parameters for an HTTP request. It is a simple container for request parameters before they are prepared for transmission. [src/requests/models.py:232-312]()

| Attribute | Type | Description |
|-----------|------|-------------|
| `method` | str | HTTP method (GET, POST, etc.) |
| `url` | str | Target URL |
| `headers` | dict | HTTP headers |
| `files` | dict | Files for multipart upload |
| `data` | various | Request body data |
| `json` | various | JSON data for body |
| `params` | dict | URL query parameters |
| `auth` | tuple/AuthBase | Authentication handler |
| `cookies` | dict/CookieJar | Cookie data |
| `hooks` | dict | Event hooks |

**Sources:** [src/requests/models.py:232-262]()

### PreparedRequest Class

The `PreparedRequest` class contains the exact bytes that will be sent to the server. It is created by calling `prepare()` on a `Request` object or `prepare_request()` on a `Session`. All request parameters are transformed into their final form. [src/requests/models.py:315-351]()

```mermaid
graph LR
    Request["Request<br/>method='GET'<br/>url='http://example.com'<br/>params={'q': 'search'}"]
    
    PreparedRequest["PreparedRequest<br/>method='GET'<br/>url='http://example.com?q=search'<br/>headers=CaseInsensitiveDict<br/>body=None"]
    
    Request -->|"prepare()"| PreparedRequest
    
    subgraph "Preparation Steps"
        PM["prepare_method()"]
        PU["prepare_url()"]
        PH["prepare_headers()"]
        PC["prepare_cookies()"]
        PB["prepare_body()"]
        PA["prepare_auth()"]
    end
    
    PreparedRequest -.-> PM
    PreparedRequest -.-> PU
    PreparedRequest -.-> PH
    PreparedRequest -.-> PC
    PreparedRequest -.-> PB
    PreparedRequest -.-> PA
```

**Sources:** [src/requests/models.py:315-351]()

Key preparation methods in `PreparedRequest`:

- `prepare_method()` - Normalizes HTTP method to uppercase [src/requests/models.py:353-356]()
- `prepare_url()` - Handles URL encoding, IDNA encoding, parameter merging [src/requests/models.py:395-449]()
- `prepare_headers()` - Creates `CaseInsensitiveDict`, validates headers [src/requests/models.py:451-468]()
- `prepare_cookies()` - Converts cookies to Cookie header [src/requests/models.py:539-550]()
- `prepare_body()` - Encodes data/files, sets Content-Type and Content-Length [src/requests/models.py:484-521]()
- `prepare_auth()` - Applies authentication handler [src/requests/models.py:552-578]()

**Sources:** [src/requests/models.py:353-578]()

## Response Object

The `Response` class represents the server's response to an HTTP request. It is built by the `HTTPAdapter` from urllib3's response object. [src/requests/models.py:600-610]()

### Response Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `status_code` | int | HTTP status code |
| `headers` | CaseInsensitiveDict | Response headers |
| `content` | bytes | Response body as bytes |
| `text` | str | Response body as unicode string |
| `url` | str | Final URL after redirects |
| `history` | list | List of Response objects from redirects |
| `encoding` | str | Encoding to decode text |
| `cookies` | RequestsCookieJar | Cookies set by server |
| `elapsed` | timedelta | Time between request and response |
| `request` | PreparedRequest | The request that generated this response |
| `raw` | urllib3.HTTPResponse | Underlying urllib3 response |

**Sources:** [src/requests/models.py:600-756]()

### Response Methods

Key methods for consuming response data:

- `json()` - Deserialize JSON response body [src/requests/models.py:910-928]()
- `raise_for_status()` - Raise HTTPError for bad status codes [src/requests/models.py:941-959]()
- `iter_content(chunk_size)` - Iterate over response content in chunks [src/requests/models.py:758-823]()
- `iter_lines()` - Iterate over response lines [src/requests/models.py:825-853]()
- `close()` - Release connection back to pool [src/requests/models.py:889-896]()

**Sources:** [src/requests/models.py:758-959]()

## Session Object

The `Session` class maintains persistent state across multiple requests, including cookies, authentication, and connection pooling. It is the recommended way to make multiple requests to the same host. [src/requests/sessions.py:357-375]()

```mermaid
graph TB
    Session["Session"]
    
    subgraph "Persistent State"
        Headers["headers<br/>CaseInsensitiveDict"]
        Cookies["cookies<br/>RequestsCookieJar"]
        Auth["auth<br/>AuthBase"]
        Proxies["proxies<br/>dict"]
        Hooks["hooks<br/>dict"]
        Verify["verify<br/>bool/str"]
        Cert["cert<br/>str/tuple"]
        MaxRedirects["max_redirects<br/>int"]
    end
    
    subgraph "Adapter Registry"
        Adapters["adapters<br/>OrderedDict"]
        HTTPAdapterHTTP["'http://' → HTTPAdapter"]
        HTTPAdapterHTTPS["'https://' → HTTPAdapter"]
    end
    
    Session --> Headers
    Session --> Cookies
    Session --> Auth
    Session --> Proxies
    Session --> Hooks
    Session --> Verify
    Session --> Cert
    Session --> MaxRedirects
    
    Session --> Adapters
    Adapters --> HTTPAdapterHTTP
    Adapters --> HTTPAdapterHTTPS
```

**Sources:** [src/requests/sessions.py:357-414]()

### Session Workflow

When making a request through a `Session`, the following steps occur:

1. **Merge Configuration**: Request parameters are merged with session defaults [src/requests/sessions.py:721-744]()
2. **Prepare Request**: `prepare_request()` creates a `PreparedRequest` [src/requests/sessions.py:452-491]()
3. **Select Adapter**: URL prefix matching selects appropriate adapter [src/requests/sessions.py:746-750]()
4. **Send Request**: Adapter's `send()` method executes the request [src/requests/sessions.py:652-664]()
5. **Handle Redirects**: Session processes redirects using `resolve_redirects()` [src/requests/sessions.py:186-294]()
6. **Update State**: Cookies are extracted and stored in session [src/requests/sessions.py:666-668]()

**Sources:** [src/requests/sessions.py:186-750]()

## Transport Adapters

Adapters provide the interface between Requests and the underlying HTTP library (urllib3). They handle connection pooling, proxy management, and TLS configuration.

### BaseAdapter

The `BaseAdapter` class defines the interface that all transport adapters must implement:

- `send(request, **kwargs)` - Send PreparedRequest, return Response [src/requests/adapters.py:126-140]()
- `close()` - Clean up adapter resources [src/requests/adapters.py:142-143]()

**Sources:** [src/requests/adapters.py:115-143]()

### HTTPAdapter

The `HTTPAdapter` is the built-in adapter that uses urllib3 for HTTP/HTTPS connections. It manages connection pools and handles protocol-level details. [src/requests/adapters.py:145-160]()

```mermaid
graph TB
    HTTPAdapter["HTTPAdapter"]
    
    subgraph "Connection Management"
        PoolManager["poolmanager<br/>urllib3.PoolManager"]
        ProxyManagers["proxy_manager<br/>dict of ProxyManagers"]
    end
    
    subgraph "Configuration"
        PoolConnections["pool_connections<br/>int (default: 10)"]
        PoolMaxsize["pool_maxsize<br/>int (default: 10)"]
        MaxRetries["max_retries<br/>urllib3.Retry"]
        PoolBlock["pool_block<br/>bool"]
    end
    
    HTTPAdapter --> PoolManager
    HTTPAdapter --> ProxyManagers
    HTTPAdapter --> PoolConnections
    HTTPAdapter --> PoolMaxsize
    HTTPAdapter --> MaxRetries
    HTTPAdapter --> PoolBlock
    
    PoolManager -->|"manages"| ConnectionPools["Connection Pools<br/>per host/port/TLS config"]
```

**Sources:** [src/requests/adapters.py:145-243]()

### HTTPAdapter Key Methods

| Method | Purpose |
|--------|---------|
| `init_poolmanager()` | Initialize urllib3 PoolManager [src/requests/adapters.py:218-243]() |
| `proxy_manager_for()` | Get or create ProxyManager for proxy URL [src/requests/adapters.py:333-358]() |
| `cert_verify()` | Configure SSL/TLS certificate verification [src/requests/adapters.py:245-283]() |
| `build_response()` | Convert urllib3 response to Response object [src/requests/adapters.py:616-664]() |
| `get_connection_with_tls_context()` | Get urllib3 connection with TLS settings [src/requests/adapters.py:314-331]() |
| `send()` | Execute PreparedRequest, return Response [src/requests/adapters.py:448-614]() |

**Sources:** [src/requests/adapters.py:218-670]()

The adapter creates separate connection pools for each unique combination of:
- Host and port
- TLS verification settings (`verify` parameter)
- Client certificate settings (`cert` parameter)

This ensures security boundaries are maintained and connections are reused efficiently. [src/requests/adapters.py:375-423]()

**Sources:** [src/requests/adapters.py:375-423]()

## Utility Components

### Data Structures

The library provides specialized data structures for HTTP-specific needs:

**CaseInsensitiveDict**

A dictionary subclass where keys are case-insensitive, used for HTTP headers. Defined in `structures.py`, it preserves the original case of keys while allowing case-insensitive lookups. [src/requests/structures.py:14-106]()

**LookupDict**

A dictionary subclass for status codes that allows both numeric and named lookups. [src/requests/structures.py:109-121]()

**RequestsCookieJar**

A `CookieJar` subclass with dictionary-like interface for easier cookie manipulation. [src/requests/cookies.py:191-411]()

**Sources:** [src/requests/structures.py:14-121](), [src/requests/cookies.py:191-411]()

### Utility Functions

The `utils` module provides essential helper functions:

| Function | Purpose |
|----------|---------|
| `super_len()` | Calculate content length for various object types [src/requests/utils.py:134-203]() |
| `get_encoding_from_headers()` | Extract charset from Content-Type header [src/requests/utils.py:527-550]() |
| `get_auth_from_url()` | Extract username/password from URL [src/requests/utils.py:110-132]() |
| `get_netrc_auth()` | Get credentials from .netrc file [src/requests/utils.py:205-247]() |
| `select_proxy()` | Select appropriate proxy for URL [src/requests/utils.py:408-418]() |
| `should_bypass_proxies()` | Check if URL should bypass proxy [src/requests/utils.py:421-482]() |
| `requote_uri()` | Re-quote URI to ensure proper encoding [src/requests/utils.py:655-680]() |
| `parse_header_links()` | Parse Link headers [src/requests/utils.py:910-942]() |
| `extract_zipped_paths()` | Extract files from zip archives [src/requests/utils.py:1001-1015]() |

**Sources:** [src/requests/utils.py:110-1015]()

## Authentication

The authentication system is based on callable objects that modify requests before they are sent.

```mermaid
graph TB
    AuthBase["AuthBase<br/>(auth.py)"]
    
    HTTPBasicAuth["HTTPBasicAuth<br/>adds Authorization header"]
    HTTPProxyAuth["HTTPProxyAuth<br/>adds Proxy-Authorization header"]
    HTTPDigestAuth["HTTPDigestAuth<br/>handles challenge-response"]
    CustomAuth["Custom Auth<br/>user-defined subclass"]
    
    AuthBase -->|"subclass"| HTTPBasicAuth
    AuthBase -->|"subclass"| HTTPProxyAuth
    AuthBase -->|"subclass"| HTTPDigestAuth
    AuthBase -->|"subclass"| CustomAuth
    
    PreparedRequest["PreparedRequest"]
    
    HTTPBasicAuth -->|"__call__()"| PreparedRequest
    HTTPProxyAuth -->|"__call__()"| PreparedRequest
    HTTPDigestAuth -->|"__call__()"| PreparedRequest
    CustomAuth -->|"__call__()"| PreparedRequest
```

**Sources:** [src/requests/auth.py:69-315]()

### AuthBase

All authentication handlers inherit from `AuthBase` and implement `__call__(r)` which receives a `PreparedRequest` and returns it after modification. [src/requests/auth.py:69-74]()

**Sources:** [src/requests/auth.py:69-74]()

### Built-in Authentication

- **HTTPBasicAuth**: Adds `Authorization` header with Base64-encoded credentials [src/requests/auth.py:76-102]()
- **HTTPProxyAuth**: Similar to HTTPBasicAuth but for proxy authentication [src/requests/auth.py:105-111]()
- **HTTPDigestAuth**: Implements HTTP Digest Authentication with challenge-response flow [src/requests/auth.py:114-315]()

**Sources:** [src/requests/auth.py:76-315]()

## Exception Hierarchy

The library defines a comprehensive exception hierarchy for different error conditions:

```mermaid
graph TB
    RequestException["RequestException<br/>(base exception)"]
    
    HTTPError["HTTPError<br/>4xx/5xx status codes"]
    ConnectionError["ConnectionError<br/>network failures"]
    Timeout["Timeout<br/>timeout errors"]
    URLRequired["URLRequired<br/>missing URL"]
    TooManyRedirects["TooManyRedirects<br/>redirect limit exceeded"]
    JSONDecodeError["JSONDecodeError<br/>JSON decode failures"]
    
    ProxyError["ProxyError<br/>proxy issues"]
    SSLError["SSLError<br/>SSL/TLS errors"]
    ConnectTimeout["ConnectTimeout<br/>connection timeout"]
    ReadTimeout["ReadTimeout<br/>read timeout"]
    
    InvalidURL["InvalidURL<br/>malformed URL"]
    MissingSchema["MissingSchema<br/>missing URL scheme"]
    InvalidSchema["InvalidSchema<br/>invalid URL scheme"]
    InvalidHeader["InvalidHeader<br/>invalid header"]
    InvalidProxyURL["InvalidProxyURL<br/>malformed proxy URL"]
    
    ContentDecodingError["ContentDecodingError<br/>content decode failure"]
    ChunkedEncodingError["ChunkedEncodingError<br/>invalid chunked encoding"]
    StreamConsumedError["StreamConsumedError<br/>stream already consumed"]
    RetryError["RetryError<br/>retry logic failure"]
    UnrewindableBodyError["UnrewindableBodyError<br/>cannot rewind body"]
    
    RequestException --> HTTPError
    RequestException --> ConnectionError
    RequestException --> Timeout
    RequestException --> URLRequired
    RequestException --> TooManyRedirects
    RequestException --> JSONDecodeError
    
    ConnectionError --> ProxyError
    ConnectionError --> SSLError
    ConnectionError --> ConnectTimeout
    
    Timeout --> ReadTimeout
    Timeout --> ConnectTimeout
    
    RequestException --> InvalidURL
    InvalidURL --> MissingSchema
    InvalidURL --> InvalidSchema
    InvalidURL --> InvalidProxyURL
    
    RequestException --> InvalidHeader
    RequestException --> ContentDecodingError
    RequestException --> ChunkedEncodingError
    RequestException --> StreamConsumedError
    RequestException --> RetryError
    RequestException --> UnrewindableBodyError
```

**Sources:** [src/requests/exceptions.py:1-153]()

All exceptions inherit from `RequestException`, which inherits from `IOError`. This allows catching all Requests-related errors with a single except clause. Each exception may have `request` and `response` attributes providing context about the failed operation. [src/requests/exceptions.py:20-35]()

**Sources:** [src/requests/exceptions.py:20-35]()

## Component Interaction Flow

The following diagram illustrates how components interact during a typical request:

```mermaid
sequenceDiagram
    participant User
    participant Session
    participant Request
    participant PreparedRequest
    participant HTTPAdapter
    participant PoolManager
    participant Response
    
    User->>Session: session.get(url, params, auth)
    Session->>Request: Create Request object
    Session->>PreparedRequest: prepare_request(Request)
    PreparedRequest->>PreparedRequest: prepare_method()
    PreparedRequest->>PreparedRequest: prepare_url()
    PreparedRequest->>PreparedRequest: prepare_headers()
    PreparedRequest->>PreparedRequest: prepare_cookies()
    PreparedRequest->>PreparedRequest: prepare_body()
    PreparedRequest->>PreparedRequest: prepare_auth()
    
    Session->>Session: Select adapter from adapters dict
    Session->>HTTPAdapter: send(PreparedRequest, verify, cert)
    HTTPAdapter->>PoolManager: connection_from_host()
    PoolManager-->>HTTPAdapter: Connection
    HTTPAdapter->>PoolManager: urlopen(method, url, body, headers)
    PoolManager-->>HTTPAdapter: urllib3.HTTPResponse
    HTTPAdapter->>Response: build_response()
    Response-->>HTTPAdapter: Response object
    HTTPAdapter-->>Session: Response
    Session->>Session: Store cookies from response
    Session-->>User: Response
```

**Sources:** [src/requests/sessions.py:452-668](), [src/requests/adapters.py:448-670](), [src/requests/models.py:232-312](), [tests/test_requests.py:87-95]()

---

# Page: Core API

# Core API

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [README.md](README.md)
- [docs/api.rst](docs/api.rst)
- [docs/community/faq.rst](docs/community/faq.rst)
- [docs/index.rst](docs/index.rst)
- [docs/user/advanced.rst](docs/user/advanced.rst)
- [docs/user/quickstart.rst](docs/user/quickstart.rst)
- [src/requests/api.py](src/requests/api.py)

</details>



The Core API of the Requests library provides the primary interface through which developers interact with the library to make HTTP requests. This document details the main functions, classes, and workflow that constitute the core functionality of Requests.

For information about authentication mechanisms, see the [Authentication](#3) page. For advanced usage patterns, refer to the [Advanced Usage](#4) page.

## Overview of Core API Components

The Core API consists of several key components that work together to provide a simple yet powerful HTTP client experience. The library is designed so that high-level convenience functions (like `get` or `post`) wrap the more complex `Session` and `Request` logic.

### Natural Language to Code Entity Space: Architecture
```mermaid
graph TD
    User["User Application"] -->|"imports"| API["requests module"]
    API -->|"exposes"| Methods["HTTP Methods<br/>requests.api.get(), post(), etc."]
    API -->|"provides"| Session["requests.sessions.Session class"]
    API -->|"defines"| Models["requests.models.Request/Response"]
    Methods -->|"creates"| ReqObj["requests.models.Request"]
    ReqObj -->|"prepared into"| PrepReq["requests.models.PreparedRequest"]
    Session -->|"sends"| PrepReq
    Session -->|"uses"| Adapters["requests.adapters.HTTPAdapter"]
    Adapters -->|"connects to"| Server["HTTP Server"]
    Server -->|"returns data to"| RespObj["requests.models.Response"]
    RespObj -->|"returned to"| User
```

Sources:
- [src/requests/api.py:24-71]()
- [docs/api.rst:13-26]()
- [docs/user/quickstart.rst:20-51]()
- [docs/user/advanced.rst:87-118]()

## Request-Response Lifecycle

This diagram illustrates the complete lifecycle of a request, from the initial API call to the returned response, highlighting the transition from high-level API to low-level transport.

### Natural Language to Code Entity Space: Lifecycle
```mermaid
sequenceDiagram
    participant User as "Python Application"
    participant API as "requests.api.get()"
    participant Req as "requests.models.Request"
    participant PrepReq as "requests.models.PreparedRequest"
    participant Session as "requests.sessions.Session"
    participant Adapter as "requests.adapters.HTTPAdapter"
    participant Server as "HTTP Server"
    
    User->>API: "calls requests.get(url, **kwargs)"
    API->>Session: "instantiates Session() context"
    Session->>Req: "creates Request object"
    Req->>PrepReq: "prepare() formats request"
    Session->>PrepReq: "merges Session.cookies & Session.headers"
    Session->>Adapter: "calls HTTPAdapter.send(request)"
    Adapter->>Server: "executes via urllib3"
    Server->>Adapter: "returns raw response"
    Adapter->>Session: "builds requests.models.Response"
    Session->>API: "returns Response object"
    API->>User: "returns Response to user"
```

Sources:
- [src/requests/api.py:70-71]()
- [docs/user/advanced.rst:87-118]()
- [docs/user/advanced.rst:120-208]()

## Main Request Methods

The primary way to interact with the Requests library is through these HTTP verb methods defined in `requests.api`. All convenience methods internally instantiate a `Session` and call its `request` method to ensure proper resource cleanup [src/requests/api.py:70-71]().

| Method | HTTP Verb | Description | Reference |
|--------|-----------|-------------|-----------|
| `requests.get()` | GET | Retrieve resources | [src/requests/api.py:74-87]() |
| `requests.post()` | POST | Create resources (supports `data` and `json`) | [src/requests/api.py:117-134]() |
| `requests.put()` | PUT | Update resources | [src/requests/api.py:137-151]() |
| `requests.delete()` | DELETE | Delete resources | [src/requests/api.py:171-178]() |
| `requests.head()` | HEAD | Get headers only (defaults `allow_redirects=False`) | [src/requests/api.py:102-114]() |
| `requests.options()` | OPTIONS | Get allowed methods | [src/requests/api.py:90-99]() |
| `requests.patch()` | PATCH | Partial update | [src/requests/api.py:154-168]() |

Each method returns a `Response` object containing the server's response [src/requests/api.py:56-57]().

Sources:
- [src/requests/api.py:24-178]()
- [docs/api.rst:19-26]()
- [docs/user/quickstart.rst:20-51]()

## Request and Response Models

Detailed documentation of these models can be found in [Request and Response Models](#2.1).

### Request Objects
The `Request` class is used to construct an HTTP request. It acts as a container for data (URL, method, headers, etc.) that will later be "prepared" for transmission [docs/user/advanced.rst:90-93]().
- **Definition**: `requests.models.Request` [docs/api.rst:53]()

### Response Objects
The `Response` class encapsulates the server's HTTP response. It provides access to the status code [docs/user/quickstart.rst:39](), headers [docs/user/quickstart.rst:41](), and content through properties like `text` [docs/user/quickstart.rst:93]() or methods like `json()` [docs/user/quickstart.rst:151]().
- **Definition**: `requests.models.Response` [src/requests/api.py:16]()

Sources:
- [docs/user/advanced.rst:87-118]()
- [docs/api.rst:52-57]()
- [docs/user/quickstart.rst:84-166]()

## Prepared Requests

The `PreparedRequest` class represents a request that's ready to be sent to the server. It is the result of calling `Request.prepare()` or `Session.prepare_request(request)` [docs/user/advanced.rst:135-172](). Using `Session.prepare_request` ensures session-level state like cookies are merged into the request [docs/user/advanced.rst:160-165]().

For details, see [Request and Response Models](#2.1).

Sources:
- [docs/user/advanced.rst:120-208]()
- [docs/api.rst:64-65]()

## Session Management

The `Session` object allows you to persist parameters (cookies, headers, auth) across multiple requests [docs/user/advanced.rst:13-18](). It also manages connection pooling via `urllib3` for performance gains when making several requests to the same host [docs/user/advanced.rst:15-18]().

For details, see [Session Management](#2.2).

Sources:
- [docs/user/advanced.rst:10-83]()
- [docs/api.rst:46-47]()
- [src/requests/api.py:70-71]()

## Transport Adapters

Transport adapters handle the actual sending of requests over the network. The default `HTTPAdapter` manages the `urllib3` connection pool and implements the `send()` method used by sessions [docs/api.rst:70-71]().

For details, see [Transport Adapters](#2.3).

Sources:
- [docs/user/advanced.rst:10-19]()
- [docs/api.rst:66-72]()

## Redirect Handling

Requests automatically follows redirects for most HTTP verbs by default [src/requests/api.py:48-49](). This behavior can be controlled per-request via the `allow_redirects` parameter [src/requests/api.py:48]().

For details, see [Redirect Handling](#2.4).

Sources:
- [src/requests/api.py:48-49]()
- [src/requests/api.py:113]()

## Error Handling

Requests provides a comprehensive exception hierarchy where all exceptions inherit from `requests.exceptions.RequestException` [docs/api.rst:31]().

| Exception | Description |
|-----------|-------------|
| `ConnectionError` | A Network problem (e.g. DNS failure, refused connection) [docs/api.rst:32]() |
| `HTTPError` | An HTTP error occurred (e.g. 404, 500) [docs/api.rst:33]() |
| `Timeout` | The request timed out [docs/api.rst:37]() |
| `TooManyRedirects` | The request exceeded the configured number of maximum redirects [docs/api.rst:34]() |
| `JSONDecodeError` | Raised by `Response.json()` if decoding fails [docs/api.rst:38]() |

Sources:
- [docs/api.rst:28-38]()
- [docs/user/quickstart.rst:154-158]()

---

# Page: Request and Response Models

# Request and Response Models

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [AUTHORS.rst](AUTHORS.rst)
- [src/requests/_types.py](src/requests/_types.py)
- [src/requests/models.py](src/requests/models.py)
- [src/requests/sessions.py](src/requests/sessions.py)
- [tests/test_requests.py](tests/test_requests.py)

</details>



## Purpose and Scope

This document explains the Request and Response model architecture in the Requests library, which forms the core foundation for HTTP communications. The document covers the `Request`, `PreparedRequest`, and `Response` classes, their attributes, and how they interact with each other throughout the HTTP request-response lifecycle.

## Overview

The Requests library follows a clear object-oriented approach to handling HTTP communications using three primary model classes:

1.  `Request`: User-created object representing an HTTP request intention. [src/requests/models.py:230-230]()
2.  `PreparedRequest`: A fully prepared and serialized request ready to be sent. [src/requests/models.py:313-313]()
3.  `Response`: Object representing the server's response to a request. [src/requests/models.py:640-640]()

### Core Models Diagram

```mermaid
classDiagram
    class RequestHooksMixin {
        +register_hook()
        +deregister_hook()
    }
    class RequestEncodingMixin {
        +path_url
        +_encode_params()
        +_encode_files()
    }
    class Request {
        +method
        +url
        +headers
        +files
        +data
        +params
        +auth
        +cookies
        +hooks
        +json
        +prepare()
    }
    class PreparedRequest {
        +method
        +url
        +headers
        +body
        +hooks
        +prepare()
        +prepare_method()
        +prepare_url()
        +prepare_headers()
        +prepare_body()
        +prepare_auth()
        +prepare_cookies()
        +prepare_hooks()
    }
    class Response {
        +status_code
        +headers
        +url
        +history
        +encoding
        +reason
        +cookies
        +elapsed
        +request
        +content
        +text
        +json()
        +raise_for_status()
        +iter_content()
        +iter_lines()
    }
    
    RequestHooksMixin <|-- Request
    RequestHooksMixin <|-- PreparedRequest
    RequestEncodingMixin <|-- PreparedRequest
    Request ..> PreparedRequest: "creates via prepare()"
    PreparedRequest <.. Response: "references via .request"
```

Sources: [src/requests/models.py:230-310](), [src/requests/models.py:313-638](), [src/requests/models.py:640-1039]()

## Request-Response Lifecycle

The following diagram illustrates the request-response lifecycle and how the three model classes interact with each other and other components of the system:

```mermaid
sequenceDiagram
    participant User as "User Code"
    participant API as "requests.api (get, post, etc)"
    participant Req as "Request"
    participant PrepReq as "PreparedRequest"
    participant Session as "Session"
    participant Adapter as "HTTPAdapter"
    participant Server as "HTTP Server"
    participant Resp as "Response"
    
    User->>API: "requests.get(url, **kwargs)"
    API->>Session: "request(method, url, **kwargs)"
    Session->>Req: "Create Request object"
    Session->>Session: "prepare_request(request)"
    Session->>Req: "prepare()"
    Req->>PrepReq: "Return PreparedRequest"
    Note over PrepReq: "Serializes inputs into<br/>transmission-ready format"
    Session->>Session: "merge_setting() for headers, auth, etc"
    Session->>Adapter: "send(prepared_request)"
    Adapter->>Server: "Make HTTP connection (urllib3)"
    Server->>Adapter: "Return raw HTTP response"
    Adapter->>Resp: "build_response(request, resp)"
    Resp->>Session: "Return Response"
    Session->>API: "Return Response"
    API->>User: "Return Response"
```

Sources: [src/requests/sessions.py:475-534](), [src/requests/sessions.py:645-710](), [src/requests/models.py:296-310]()

## Request Class

The `Request` class is the starting point in the request-response cycle. It represents a user's intention to make an HTTP request and holds all the parameters that define the request before it is prepared for transmission. [src/requests/models.py:230-258]()

### Request Class Attributes

| Attribute | Description |
|-----------|-------------|
| `method` | HTTP method (GET, POST, PUT, etc.) |
| `url` | URL to send the request to |
| `headers` | Dictionary of HTTP headers |
| `files` | Dictionary of files for multipart uploads |
| `data` | Request body or form data |
| `json` | JSON data to be sent in the request body |
| `params` | URL parameters to append to the URL |
| `auth` | Authentication handler or (user, pass) tuple |
| `cookies` | Dictionary or CookieJar of cookies |
| `hooks` | Dictionary of callback hooks |

Sources: [src/requests/models.py:238-258]()

## PreparedRequest Class

The `PreparedRequest` class is a fully prepared HTTP request with the exact bytes that will be sent to the server. This class handles much of the complex logic required to transform user-provided inputs into a proper HTTP request. [src/requests/models.py:313-336]()

### Preparation Methods

The `prepare()` method orchestrates the preparation by calling specialized methods: [src/requests/models.py:364-378]()

*   `prepare_method(method)`: Normalizes the HTTP method to uppercase. [src/requests/models.py:380-384]()
*   `prepare_url(url, params)`: Validates and formats the URL, handles IDNA encoding, and appends parameters. [src/requests/models.py:386-455]()
*   `prepare_headers(headers)`: Converts headers to `CaseInsensitiveDict` and validates them using `check_header_validity`. [src/requests/models.py:457-476]()
*   `prepare_body(data, files, json)`: Serializes the request body, handling JSON via `complexjson`, multipart/form-data via `_encode_files`, or form-encoded content via `_encode_params`. [src/requests/models.py:503-587]()
*   `prepare_auth(auth, url)`: Applies authentication (e.g., `HTTPBasicAuth`) to the request. [src/requests/models.py:589-609]()
*   `prepare_cookies(cookies)`: Adds cookies to the request headers using `get_cookie_header`. [src/requests/models.py:610-628]()

Sources: [src/requests/models.py:364-628](), [src/requests/utils.py:73-83]()

## Response Class

The `Response` class represents the server's response to an HTTP request. [src/requests/models.py:640-640]()

### Response Attributes and Methods

| Attribute/Method | Description |
|------------------|-------------|
| `status_code` | Integer HTTP status code. [src/requests/models.py:645-645]() |
| `headers` | `CaseInsensitiveDict` of response headers. [src/requests/models.py:651-651]() |
| `content` | Raw bytes of the response body. [src/requests/models.py:868-893]() |
| `text` | Decoded string content using `encoding`. [src/requests/models.py:895-925]() |
| `json()` | Returns the JSON-decoded content using `complexjson`. [src/requests/models.py:968-1002]() |
| `ok` | Boolean: `True` if `status_code` is between 200 and 299. [src/requests/models.py:758-767]() |
| `is_redirect` | Boolean: `True` if status code is in `REDIRECT_STATI`. [src/requests/models.py:769-775]() |
| `raise_for_status()` | Raises `HTTPError` if an error occurred (4xx or 5xx). [src/requests/models.py:1004-1031]() |

Sources: [src/requests/models.py:640-1039]()

## Model Inheritance and Mixins

The library uses Mixins to provide common functionality to Request and PreparedRequest objects.

```mermaid
graph TD
    subgraph "Mixins"
        HooksMixin["RequestHooksMixin<br/>(src/requests/models.py:206)<br/>+ register_hook()<br/>+ deregister_hook()"]
        EncodingMixin["RequestEncodingMixin<br/>(src/requests/models.py:108)<br/>+ path_url<br/>+ _encode_params()<br/>+ _encode_files()"]
    end

    Request["Request<br/>(src/requests/models.py:230)"]
    PreparedRequest["PreparedRequest<br/>(src/requests/models.py:313)"]
    Response["Response<br/>(src/requests/models.py:640)"]

    HooksMixin --> Request
    HooksMixin --> PreparedRequest
    EncodingMixin --> PreparedRequest
```

Sources: [src/requests/models.py:108-204](), [src/requests/models.py:206-227](), [src/requests/models.py:230-230](), [src/requests/models.py:313-313]()

## Data Flow Between Model Classes

The data flow from raw user input to the final processed output involves several stages of transformation:

```mermaid
flowchart LR
    subgraph "Input Space"
        data["data / json / files"]
        params["params"]
        auth["auth / cookies"]
    end

    subgraph "Request Layer"
        req_obj["Request Object<br/>(src/requests/models.py:230)"]
        prep_obj["PreparedRequest<br/>(src/requests/models.py:313)"]
    end

    subgraph "Network Layer"
        adapter["HTTPAdapter<br/>(src/requests/adapters.py:93)"]
        pool["urllib3 PoolManager"]
    end

    subgraph "Response Layer"
        resp_obj["Response Object<br/>(src/requests/models.py:640)"]
    end

    data --> req_obj
    params --> req_obj
    auth --> req_obj

    req_obj --> |"prepare()"| prep_obj
    prep_obj --> |"Session.send()"| adapter
    adapter --> |"urlopen()"| pool
    pool --> |"Network IO"| resp_obj
    
    resp_obj --> |"r.text / r.json()"| user["User Result"]
```

Sources: [src/requests/models.py:296-310](), [src/requests/sessions.py:645-710](), [src/requests/adapters.py:475-534]()

## Redirection Handling

When a response is a redirect (status codes defined in `REDIRECT_STATI`), the `Session` handles the creation of a new `PreparedRequest` for the redirect target. The previous response is stored in the `history` attribute of the final response. [src/requests/sessions.py:186-200](), [src/requests/models.py:95-101]()

Sources: [src/requests/sessions.py:186-200](), [src/requests/models.py:777-781]()

---

# Page: Session Management

# Session Management

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [AUTHORS.rst](AUTHORS.rst)
- [docs/api.rst](docs/api.rst)
- [docs/user/advanced.rst](docs/user/advanced.rst)
- [docs/user/quickstart.rst](docs/user/quickstart.rst)
- [src/requests/_types.py](src/requests/_types.py)
- [src/requests/auth.py](src/requests/auth.py)
- [src/requests/cookies.py](src/requests/cookies.py)
- [src/requests/sessions.py](src/requests/sessions.py)
- [tests/test_requests.py](tests/test_requests.py)

</details>



This document provides a technical overview of the Session management system in the Requests library. The Session object allows for the persistence of certain parameters and settings across multiple HTTP requests, enabling efficient connection reuse and consistent state management.

## Purpose and Benefits

The `Session` object is the primary entry point for managing persistent state and connection reuse.

- **Cookie Persistence**: Automatically extracts cookies from responses and includes them in subsequent requests using a `RequestsCookieJar` [src/requests/sessions.py:25]().
- **Connection Pooling**: Reuses underlying TCP connections via `urllib3`'s connection pooling, reducing latency for multiple requests to the same host [docs/user/advanced.rst:13-18]().
- **Configuration Persistence**: Maintains default authentication, headers, and proxy settings [src/requests/sessions.py:5-7]().
- **Performance**: Significant performance increases when making several requests to the same host [docs/user/advanced.rst:18]().

Sources: [src/requests/sessions.py:5-7](), [docs/user/advanced.rst:8-20]()

## Session Architecture and Code Entities

The following diagram maps the logical components of session management to the specific classes and files in the codebase.

```mermaid
classDiagram
    class "Session" {
        <<src/requests/sessions.py>>
        +headers: CaseInsensitiveDict
        +auth: AuthType
        +proxies: dict
        +hooks: dict
        +params: dict
        +cookies: RequestsCookieJar
        +adapters: OrderedDict
        +mount(prefix, adapter)
        +prepare_request(request)
        +send(request, **kwargs)
        +request(method, url, ...)
    }
    
    class "SessionRedirectMixin" {
        <<src/requests/sessions.py>>
        +resolve_redirects()
        +get_redirect_target()
        +should_strip_auth()
    }

    class "HTTPAdapter" {
        <<src/requests/adapters.py>>
        +poolmanager: PoolManager
        +send(request, ...)
        +build_response()
    }

    class "RequestsCookieJar" {
        <<src/requests/cookies.py>>
        +set_cookie()
        +update()
    }

    "Session" --|> "SessionRedirectMixin" : "inherits"
    "Session" o-- "RequestsCookieJar" : "cookies"
    "Session" o-- "HTTPAdapter" : "mounts via adapters"
    "Session" ..> "PreparedRequest" : "prepares/sends"
```

Sources: [src/requests/sessions.py:127-132](), [src/requests/sessions.py:355-440](), [src/requests/cookies.py:100-101](), [src/requests/sessions.py:442-450]()

## Request Lifecycle within a Session

When a request is initiated through a `Session`, it undergoes preparation and merging before being dispatched through a Transport Adapter.

```mermaid
sequenceDiagram
    participant U as User Code
    participant S as Session (src/requests/sessions.py)
    participant PR as PreparedRequest (src/requests/models.py)
    participant A as HTTPAdapter (src/requests/adapters.py)
    participant U3 as urllib3.PoolManager

    U->>S: "session.get(url, params=...)"
    S->>S: "create Request()"
    S->>S: "prepare_request(request)"
    Note over S: Merges session.headers, <br/>session.auth, session.cookies
    S->>PR: "PR.prepare(...)"
    S->>S: "merge_environment_settings()"
    Note over S: Checks REQUESTS_CA_BUNDLE, <br/>HTTP_PROXY, etc.
    S->>A: "adapter.send(prepared_request)"
    A->>U3: "connection_from_url()"
    U3-->>A: reused or new connection
    A->>U: return Response
    S->>S: "extract_cookies_to_jar()"
```

Sources: [src/requests/sessions.py:475-500](), [src/requests/sessions.py:645-670](), [src/requests/sessions.py:720-745](), [src/requests/sessions.py:757-765]()

## Configuration Merging

Sessions use a "merge" logic to combine session-level settings with method-level overrides. This is handled by `merge_setting` and `merge_hooks`.

| Setting Type | Logic | Implementation |
| :--- | :--- | :--- |
| **Dictionaries** (Headers, Params) | Merged. Method-level keys override session-level keys. | [src/requests/sessions.py:76-105]() |
| **Omission** | Setting a method-level key to `None` removes it from the request. | [docs/user/advanced.rst:76-80]() |
| **Hooks** | Session and Request hooks are combined into lists. | [src/requests/sessions.py:108-124]() |
| **Simple Types** (Auth, Verify) | Method-level strictly overrides Session-level. | [src/requests/sessions.py:90-94]() |

Sources: [src/requests/sessions.py:76-124](), [docs/user/advanced.rst:44-49]()

## Cookie Management

The `Session` object stores cookies in a `RequestsCookieJar`. Unlike standard dictionaries, this structure allows for domain and path-specific storage.

- **Automatic Extraction**: After every request, `extract_cookies_to_jar` is called to update the session's state from the `Set-Cookie` headers in the response [src/requests/sessions.py:27]().
- **Manual Manipulation**: Users can manually add cookies to `session.cookies` using `cookiejar_from_dict` [src/requests/cookies.py:98]().
- **Merging**: During request preparation, session cookies are merged with any cookies passed to the request method via `merge_cookies` [src/requests/sessions.py:28]().
- **Mock Interfaces**: Requests uses `MockRequest` and `MockResponse` to bridge its models with the `http.cookiejar.CookieJar` expectations [src/requests/cookies.py:31-134]().

Sources: [src/requests/sessions.py:24-29](), [docs/user/advanced.rst:63-65](), [src/requests/cookies.py:191-207]()

## Connection Pooling and Adapters

The `Session` manages a mapping of URL prefixes to `HTTPAdapter` instances in the `self.adapters` attribute [src/requests/sessions.py:433]().

- **Default Adapters**: By default, `Session` mounts an `HTTPAdapter` for `http://` and `https://` [src/requests/sessions.py:465-470]().
- **Prefix Matching**: When sending a request, the session iterates through its adapters and selects the one with the longest matching prefix for the target URL [src/requests/sessions.py:748-755]().
- **Pool Management**: Each `HTTPAdapter` contains a `urllib3.PoolManager`, which maintains the actual socket connections [docs/api.rst:70-72]().

Sources: [src/requests/sessions.py:748-760](), [docs/api.rst:70-72](), [src/requests/sessions.py:433-440]()

## Redirect Handling

Redirect logic is encapsulated in the `SessionRedirectMixin` [src/requests/sessions.py:127]().

- **History**: Redirect responses are stored in the `response.history` list [src/requests/sessions.py:200]().
- **Auth Stripping**: The session automatically strips the `Authorization` header when redirecting to a different hostname or port to prevent credential leakage [src/requests/sessions.py:154-184]().
- **Manual Control**: Users can set `session.max_redirects` (default 30) or pass `allow_redirects=False` to individual calls [src/requests/sessions.py:40-42]().

Sources: [src/requests/sessions.py:127-184](), [src/requests/sessions.py:186-205](), [src/requests/models.py:40-41]()

## Resource Management

`Session` objects should be closed to release underlying connections.

```python
# Context manager ensures session.close() is called
with requests.Session() as s:
    s.get('https://httpbin.org/get')
```

The `close()` method iterates through all mounted adapters and calls their respective `close()` methods to shut down connection pools [src/requests/sessions.py:795-800]().

Sources: [src/requests/sessions.py:795-805](), [docs/user/advanced.rst:67-73]()

---

# Page: Transport Adapters

# Transport Adapters

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [AUTHORS.rst](AUTHORS.rst)
- [docs/api.rst](docs/api.rst)
- [docs/user/advanced.rst](docs/user/advanced.rst)
- [docs/user/quickstart.rst](docs/user/quickstart.rst)
- [src/requests/adapters.py](src/requests/adapters.py)
- [tests/test_adapters.py](tests/test_adapters.py)
- [tests/test_requests.py](tests/test_requests.py)

</details>



## Purpose and Overview

Transport Adapters in the Requests library provide a mechanism to define and customize how HTTP requests are made. They serve as an abstraction layer between the high-level `Session` interface and the underlying connection handling, allowing for precise control over connection behaviors, such as SSL configuration, connection pooling, and proxy support [src/requests/adapters.py:1-7]().

This document explains the Transport Adapter system, its architecture, how to use the built-in `HTTPAdapter`, and how to customize transport behavior with custom adapters.

Sources: [src/requests/adapters.py:1-7](), [docs/user/advanced.rst:96-118]()

## Transport Adapter Architecture

Transport Adapters form a critical part of the Requests library's modular design. The architecture follows a pattern where different URL schemes can be handled by different adapter implementations.

### Architecture Diagram: Code Entity Space

This diagram shows the relationship between core classes in the transport layer, specifically focusing on how `HTTPAdapter` bridges Requests models to `urllib3` entities.

```mermaid
classDiagram
    class "Session" {
        +adapters: OrderedDict
        +mount(prefix, adapter)
        +send(request, **kwargs)
    }
    
    class "BaseAdapter" {
        +send(request, stream, timeout, verify, cert, proxies)
        +close()
    }
    
    class "HTTPAdapter" {
        +poolmanager: PoolManager
        +proxy_manager: dict
        +max_retries: Retry
        +init_poolmanager(connections, maxsize, block)
        +get_connection(url, proxies)
        +send(request, stream, timeout, verify, cert, proxies)
        +build_response(req, resp)
    }
    
    class "PoolManager" {
        <<urllib3>>
        +connection_from_url(url)
    }
    
    class "ProxyManager" {
        <<urllib3>>
        +connection_from_url(url)
    }

    class "PreparedRequest" {
        +url: str
        +headers: CaseInsensitiveDict
        +body: bytes
    }
    
    "Session" o-- "BaseAdapter" : "mounts via prefix"
    "BaseAdapter" <|-- "HTTPAdapter" : "implements [src/requests/adapters.py:158]"
    "HTTPAdapter" --> "PoolManager" : "manages [src/requests/adapters.py:199]"
    "HTTPAdapter" --> "ProxyManager" : "creates via proxy_from_url [src/requests/adapters.py:31]"
    "HTTPAdapter" ..> "PreparedRequest" : "consumes in send() [src/requests/adapters.py:440]"
```

Sources: [src/requests/adapters.py:122-156](), [src/requests/adapters.py:158-200](), [src/requests/adapters.py:304-357](), [docs/user/advanced.rst:8-21]()

## How Adapters Work Within Requests

When a `Session` sends a request, it selects the appropriate adapter based on the URL's prefix. This is done by iterating through the `adapters` OrderedDict and matching the prefix against the request URL [docs/user/advanced.rst:163-189]().

### Request Flow Diagram

```mermaid
sequenceDiagram
    participant S as "Session.send()"
    participant AM as "Session.adapters"
    participant HA as "HTTPAdapter.send()"
    participant PM as "urllib3.PoolManager"
    participant R as "Response"

    S->>AM: find_adapter(request.url)
    AM-->>S: returns HTTPAdapter
    S->>HA: send(prepared_request, ...)
    HA->>HA: get_connection(request.url) [src/requests/adapters.py:458]
    HA->>PM: connection_from_url() [src/requests/adapters.py:315]
    PM-->>HA: returns ConnectionPool
    HA->>HA: low_level_send()
    HA->>R: build_response(prepared_request, low_level_resp) [src/requests/adapters.py:613]
    R-->>HA: returns Response object
    HA-->>S: returns Response object
```

Sources: [src/requests/adapters.py:440-534](), [src/requests/adapters.py:613-676](), [docs/user/advanced.rst:143-152]()

## The Default HTTPAdapter

Requests ships with the `HTTPAdapter`, which provides the default interaction with HTTP and HTTPS using the `urllib3` library [src/requests/adapters.py:158-165]().

### Key Configuration Parameters

The `HTTPAdapter` constructor allows tuning the underlying `urllib3` connection pools [src/requests/adapters.py:201-207]().

| Parameter | Description | Default |
|-----------|-------------|---------|
| `pool_connections` | The number of `urllib3` connection pools to cache [src/requests/adapters.py:166]() | 10 [src/requests/adapters.py:80]() |
| `pool_maxsize` | The maximum number of connections to save in the pool [src/requests/adapters.py:167]() | 10 [src/requests/adapters.py:80]() |
| `max_retries` | The maximum number of retries each connection should attempt [src/requests/adapters.py:168]() | 0 [src/requests/adapters.py:81]() |
| `pool_block` | Whether the connection pool should block for connections [src/requests/adapters.py:175]() | False [src/requests/adapters.py:79]() |

Sources: [src/requests/adapters.py:79-82](), [src/requests/adapters.py:158-183](), [src/requests/adapters.py:201-223]()

## Custom Transport Adapters

Custom adapters allow developers to modify how Requests interacts with the network by subclassing `HTTPAdapter` or `BaseAdapter` [src/requests/adapters.py:122-123]().

### Implementation: Custom SSL Version

A common use case is forcing a specific SSL version by overriding `init_poolmanager` [src/requests/adapters.py:240-241]().

```python
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

class SslAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        # This method is called by __init__ to set up the PoolManager
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=ssl.PROTOCOL_TLSv1_2
        )
```

Sources: [src/requests/adapters.py:240-265](), [docs/user/advanced.rst:190-205]()

## Connection Pool Management

The `HTTPAdapter` manages `urllib3` connection pools to enable persistent connections [docs/user/advanced.rst:10-18]().

### Connection Reuse Logic

The `get_connection` method is responsible for returning an appropriate `urllib3` connection pool for the given URL, taking proxies into account [src/requests/adapters.py:304-306]().

```mermaid
flowchart TD
    subgraph "HTTPAdapter.get_connection(url, proxies)"
        A["Parse URL [src/requests/adapters.py:307]"] --> B{"Proxy for URL? [src/requests/adapters.py:317]"}
        B -- "Yes" --> C["proxy_manager_for(proxy) [src/requests/adapters.py:326]"]
        B -- "No" --> D["poolmanager.connection_from_url(url) [src/requests/adapters.py:315]"]
        C --> E["Return Connection Pool"]
        D --> E
    end
```

Connections are retrieved based on the scheme, host, and port of the request [src/requests/adapters.py:304-315](). If a proxy is configured via the `proxies` dictionary, the adapter uses `proxy_manager_for` to retrieve or create a `ProxyManager` [src/requests/adapters.py:326-340]().

Sources: [src/requests/adapters.py:304-357](), [src/requests/adapters.py:266-302](), [docs/user/advanced.rst:13-19]()

## SSL and Certificate Handling

The adapter is responsible for configuring SSL context via the `cert_verify` method and internal `_urllib3_request_context` helper [src/requests/adapters.py:225-226, 85-90]().

- **Verification**: If `verify` is a string, it is treated as a path to a CA bundle or directory [src/requests/adapters.py:100-104](). If `False`, certificate requirements are set to `CERT_NONE` [src/requests/adapters.py:98-99]().
- **Client Certificates**: The `cert` parameter can be a single file path or a tuple containing (cert, key) [src/requests/adapters.py:106-113]().

These settings are processed in `_urllib3_request_context` to generate the `pool_kwargs` consumed by the `urllib3` pool during the request lifecycle [src/requests/adapters.py:85-119]().

Sources: [src/requests/adapters.py:85-119](), [src/requests/adapters.py:225-238](), [docs/user/advanced.rst:211-230]()

## Response Construction

After `urllib3` returns a low-level response, the adapter calls `build_response` to create a `requests.Response` object [src/requests/adapters.py:613-614]().

Key steps in `build_response`:
1. Initialize a new `Response` object [src/requests/adapters.py:633]().
2. Populate status code, headers, and encoding [src/requests/adapters.py:636-640]().
3. Attach the original `PreparedRequest` [src/requests/adapters.py:650]().
4. Extract cookies from the response into the `CookieJar` using `extract_cookies_to_jar` [src/requests/adapters.py:653]().

Sources: [src/requests/adapters.py:613-676](), [src/requests/cookies.py:38]()

---

# Page: Redirect Handling

# Redirect Handling

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [AUTHORS.rst](AUTHORS.rst)
- [src/requests/_types.py](src/requests/_types.py)
- [src/requests/sessions.py](src/requests/sessions.py)
- [tests/test_lowlevel.py](tests/test_lowlevel.py)
- [tests/test_requests.py](tests/test_requests.py)
- [tests/test_testserver.py](tests/test_testserver.py)
- [tests/test_utils.py](tests/test_utils.py)

</details>



## Purpose and Scope

This page documents how the Requests library handles HTTP redirects (3xx status codes), including status code interpretation, method transformation, header and body handling, and redirect chain tracking. This covers the automatic following of redirect responses and the configuration options available to control redirect behavior.

For information about the broader request/response lifecycle, see [Request and Response Models](#2.1). For session-level configuration that affects redirects, see [Session Management](#2.2).

---

## Overview

HTTP redirects occur when a server responds with a 3xx status code and a `Location` header indicating where the client should redirect to. The Requests library automatically follows redirects for most HTTP methods, building a redirect history chain and applying appropriate transformations to the request method, headers, and body based on the redirect status code.

By default, redirects are followed automatically for `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, and `OPTIONS` methods, but not for `HEAD` [src/requests/sessions.py:596-597](). The redirect behavior can be controlled via the `allow_redirects` parameter on request methods and the `max_redirects` attribute on `Session` objects [src/requests/sessions.py:128]().

**Key Concepts:**
- **Redirect Status Codes**: 301, 302, 303, 307, 308 (defined in `REDIRECT_STATI` [src/requests/models.py:41]()).
- **Method Transformation**: Certain status codes change POST/PUT/PATCH to GET [src/requests/sessions.py:238-251]().
- **Redirect History**: Each intermediate response is tracked in `Response.history` [src/requests/sessions.py:200]().
- **Header Stripping**: Sensitive headers are removed during cross-origin redirects [src/requests/sessions.py:154-184]().
- **Body Removal**: Request body is removed when method changes to GET [src/requests/sessions.py:255-263]().

Sources: [src/requests/models.py:41](), [src/requests/sessions.py:127-290](), [tests/test_requests.py:214-218]()

---

## Redirect Status Codes and Behavior

The set of status codes that trigger redirect handling is defined in `requests.models.REDIRECT_STATI` [src/requests/models.py:41]().

| Status Code | Name | Method Transformation | Body Handling |
|-------------|------|----------------------|---------------|
| 301 | Moved Permanently | POST/PUT/PATCH → GET, HEAD/GET preserved | Body removed on transformation |
| 302 | Found | POST/PUT/PATCH → GET, HEAD/GET preserved | Body removed on transformation |
| 303 | See Other | POST/PUT/PATCH/DELETE → GET, HEAD preserved | Body removed on transformation |
| 307 | Temporary Redirect | Method preserved | Body preserved |
| 308 | Permanent Redirect | Method preserved | Body preserved |

### Redirect Logic Flow

```mermaid
graph TD
    Start["Request Method"]
    Status["Redirect Status Code"]
    
    Start --> Status
    
    Status -->|"301/302"| Transform301["POST/PUT/PATCH → GET<br/>HEAD → HEAD<br/>GET → GET"]
    Status -->|"303"| Transform303["All methods → GET<br/>(except HEAD → HEAD)"]
    Status -->|"307/308"| Preserve["Method Preserved"]
    
    Transform301 --> RemoveBody["Remove body if<br/>method changed"]
    Transform303 --> RemoveBody
    Preserve --> KeepBody["Keep body if<br/>seekable"]
    
    RemoveBody --> StripHeaders["Strip Content-Length,<br/>Content-Type,<br/>Transfer-Encoding"]
    KeepBody --> Location["Follow Location header"]
    StripHeaders --> Location
    
    Location --> NextRequest["Execute redirected request"]
```

Sources: [src/requests/sessions.py:238-270](), [src/requests/models.py:41](), [tests/test_requests.py:214-218]()

---

## Redirect History Chain

Each time a redirect is followed, the intermediate `Response` object is added to the `Response.history` list [src/requests/sessions.py:200](). The final response contains the complete redirect chain, allowing inspection of each redirect step.

### Sequence of Redirection

```mermaid
sequenceDiagram
    participant Client
    participant Session as "Session.resolve_redirects"
    participant Adapter as "HTTPAdapter"
    participant Server
    
    Client->>Session: request("http://example.com/path")
    Session->>Adapter: send(PreparedRequest)
    Adapter->>Server: GET /path
    Server-->>Adapter: 302 Found<br/>Location: /new-path
    Adapter-->>Session: Response (status=302)
    
    Note over Session: Add to history list
    Session->>Session: prepare redirect request
    Session->>Adapter: send(PreparedRequest)
    Adapter->>Server: GET /new-path
    Server-->>Adapter: 301 Moved<br/>Location: /final
    Adapter-->>Session: Response (status=301)
    
    Note over Session: Add to history list
    Session->>Session: prepare redirect request
    Session->>Adapter: send(PreparedRequest)
    Adapter->>Server: GET /final
    Server-->>Adapter: 200 OK
    Adapter-->>Session: Response (status=200)
    
    Session-->>Client: Response(status=200,<br/>history=[302 Response, 301 Response])
```

Sources: [src/requests/sessions.py:186-290](), [tests/test_requests.py:214-218]()

---

## Configuration Options

### allow_redirects Parameter

The `allow_redirects` parameter controls whether redirects are followed for a specific request. It is passed through the `Session.request` method down to `Session.send` [src/requests/sessions.py:511]().

### max_redirects Setting

The `max_redirects` attribute on a `Session` limits the number of redirects to prevent infinite redirect loops [src/requests/sessions.py:128](). The default is 30, defined by `DEFAULT_REDIRECT_LIMIT` [src/requests/models.py:40]().

```mermaid
graph LR
    Request["Initial Request"]
    Count["Redirect Counter = 0"]
    
    Request --> Count
    Count --> Follow["Follow redirect"]
    Follow --> Increment["Counter += 1"]
    Increment --> Check{"Counter ><br/>max_redirects?"}
    Check -->|"No"| Follow
    Check -->|"Yes"| Exception["Raise TooManyRedirects"]
    Check -->|"No redirects"| Success["Return Response"]
```

Sources: [src/requests/sessions.py:128](), [src/requests/models.py:40](), [src/requests/sessions.py:211-213]()

---

## Header and Body Handling During Redirects

### Headers Removed on Method Transformation

When a redirect causes the request method to change from POST/PUT/PATCH to GET (status codes 301, 302, 303), the following headers are automatically removed in `resolve_redirects` [src/requests/sessions.py:255-263]():

- `Content-Length`
- `Content-Type`
- `Transfer-Encoding`

### Body Handling for 307/308 Redirects

For 307 and 308 redirects, the request body is preserved. However, the body must be seekable (support `.seek()` method) or an `UnrewindableBodyError` will be raised. Requests uses `requests.utils.rewind_body` to reset the stream position [src/requests/sessions.py:56]().

```mermaid
graph TD
    Redirect["Receive Redirect Response"]
    CheckMethod{"Method<br/>changed?"}
    
    Redirect --> CheckMethod
    CheckMethod -->|"Yes (POST→GET)"| RemoveHeaders["Remove:<br/>• Content-Length<br/>• Content-Type<br/>• Transfer-Encoding"]
    CheckMethod -->|"No (307/308)"| KeepHeaders["Preserve all headers"]
    
    RemoveHeaders --> RemoveBody["Set request.body = None"]
    KeepHeaders --> CheckBody{"Body<br/>seekable?"}
    
    CheckBody -->|"Yes"| RewindBody["Rewind body to start"]
    CheckBody -->|"No"| BodyError["Raise UnrewindableBodyError"]
    
    RemoveBody --> PrepareNext["Prepare next request"]
    RewindBody --> PrepareNext
```

Sources: [src/requests/sessions.py:186-290](), [src/requests/sessions.py:56](), [src/requests/exceptions.py:49]()

---

## Cross-Origin Redirect Considerations

### Authorization Header Stripping

The `SessionRedirectMixin.should_strip_auth` method determines if the `Authorization` header should be removed [src/requests/sessions.py:154-184](). It returns `True` if:
1. The hostname changes [src/requests/sessions.py:158-159]().
2. The port changes (unless it's a standard HTTP -> HTTPS transition on default ports) [src/requests/sessions.py:164-184]().

### Proxy-Authorization Headers

The `Proxy-Authorization` header is stripped during redirects in `resolve_redirects` because proxy authentication is typically hop-by-hop and connection-specific [src/requests/sessions.py:253]().

Sources: [src/requests/sessions.py:154-184](), [src/requests/sessions.py:253]()

---

## Implementation Details

### SessionRedirectMixin

The core redirect handling logic is implemented in the `SessionRedirectMixin` class [src/requests/sessions.py:127]().

**Key Methods:**
- `get_redirect_target(resp)`: Extracts and normalizes the `Location` header [src/requests/sessions.py:134-152](). It re-encodes location headers in latin1 before decoding as utf8 to handle incorrect encoding by underlying HTTP modules [src/requests/sessions.py:149-151]().
- `should_strip_auth(old_url, new_url)`: Logic for security-based header removal [src/requests/sessions.py:154-184]().
- `resolve_redirects(resp, req, ...)`: The main generator that manages the redirect loop, history, and request preparation [src/requests/sessions.py:186-290]().

```mermaid
graph TB
    Session["Session"]
    Mixin["SessionRedirectMixin"]
    Method["resolve_redirects()"]
    
    Session -.->|"inherits"| Mixin
    Mixin --> Method
    
    Method --> Extract["get_redirect_target()"]
    Extract --> StripAuth["should_strip_auth()"]
    StripAuth --> Transform["Transform method if needed"]
    Transform --> PrepBody["rewind_body()"]
    PrepBody --> BuildReq["Build new PreparedRequest"]
    BuildReq --> Send["Session.send()"]
    Send --> AddHistory["Update history"]
```

Sources: [src/requests/sessions.py:127-290](), [src/requests/models.py:41]()

---

# Page: Authentication

# Authentication

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [docs/community/recommended.rst](docs/community/recommended.rst)
- [docs/user/authentication.rst](docs/user/authentication.rst)
- [src/requests/auth.py](src/requests/auth.py)
- [src/requests/cookies.py](src/requests/cookies.py)

</details>



This document provides an overview of the authentication system in the Requests library. It explains how to use the built-in authentication mechanisms, integrate with external authentication libraries, and create custom authentication handlers for specialized requirements.

## Authentication System Overview

The Requests library provides a flexible authentication system built around the `AuthBase` class [src/requests/auth.py:78-82](). This system allows you to authenticate with various HTTP authentication schemes and easily create custom authentication handlers.

Authentication in Requests works by modifying `PreparedRequest` objects before they are sent to the server. This happens through the `__call__` method of authentication objects, which gets called with the prepared request as an argument [src/requests/auth.py:81-82]().

The diagram below maps the natural language concepts to the code entities within the `requests.auth` module:

### Authentication Class Hierarchy

```mermaid
classDiagram
    class AuthBase["requests.auth.AuthBase"] {
        "__call__(r: PreparedRequest)"
    }
    
    class HTTPBasicAuth["requests.auth.HTTPBasicAuth"] {
        "username: str|bytes"
        "password: str|bytes"
        "__call__(r: PreparedRequest)"
    }
    
    class HTTPDigestAuth["requests.auth.HTTPDigestAuth"] {
        "username: str|bytes"
        "password: str|bytes"
        "_thread_local: threading.local"
        "__call__(r: PreparedRequest)"
    }
    
    class HTTPProxyAuth["requests.auth.HTTPProxyAuth"] {
        "__call__(r: PreparedRequest)"
    }
    
    AuthBase <|-- HTTPBasicAuth
    AuthBase <|-- HTTPDigestAuth
    HTTPBasicAuth <|-- HTTPProxyAuth
```

Sources: [src/requests/auth.py:78-124](), [docs/user/authentication.rst:125-132]()

## Authentication Flow

When a request is initiated, the `Session` or convenience functions prepare the request. If an `auth` parameter is provided, the handler's `__call__` method is invoked to apply credentials (typically by injecting headers like `Authorization`).

```mermaid
sequenceDiagram
    participant User["User Code"]
    participant Session["requests.sessions.Session"]
    participant Auth["requests.auth.AuthBase Subclass"]
    participant PrepReq["requests.models.PreparedRequest"]
    participant Server["Remote HTTP Server"]
    
    User->>Session: "get(url, auth=auth_obj)"
    Session->>PrepReq: "prepare_request(request)"
    Session->>Auth: "__call__(prepared_request)"
    Auth->>PrepReq: "r.headers['Authorization'] = ... "
    Session->>Server: "send(prepared_request)"
    Server-->>Session: "HTTP Response"
    Session-->>User: "Response object"
```

Sources: [src/requests/auth.py:111-113](), [docs/user/authentication.rst:138-142]()

## Built-in Authentication Methods

### Basic Authentication
HTTP Basic Authentication is supported natively. Requests provides a shorthand where passing a `(username, password)` tuple is automatically converted into an `HTTPBasicAuth` object [docs/user/authentication.rst:26-33](). Internally, this uses the `_basic_auth_str` utility to generate the `Authorization` header by encoding credentials in `latin1` and base64 [src/requests/auth.py:34-75]().

For details, see [Basic Authentication](#3.1).

### Digest Authentication
Digest Authentication is more complex, involving a challenge-response flow. This is handled by `HTTPDigestAuth`, which maintains state (such as nonces and challenge details) using `threading.local` to remain thread-safe [src/requests/auth.py:124-146](). It supports multiple algorithms including MD5, SHA-256, and SHA-512 [src/requests/auth.py:174-208]().

For details, see [Digest Authentication](#3.2).

### netrc Support
If no `auth` argument is provided, Requests attempts to find credentials in the user's `.netrc` file based on the hostname [docs/user/authentication.rst:39-42](). Requests searches for this file at `~/.netrc`, `~/_netrc`, or a path defined by the `NETRC` environment variable [docs/user/authentication.rst:47-50](). This behavior can be disabled by setting `trust_env=False` on a `Session` [docs/user/authentication.rst:51-56]().

Sources: [docs/user/authentication.rst:13-56](), [src/requests/auth.py:34-208]()

## External and Custom Authentication

### OAuth 1 & 2
Requests supports OAuth through the `requests-oauthlib` extension. It allows for the "OAuth dance" to be performed automatically [docs/community/recommended.rst:45-53]().
* **OAuth 1**: Used for APIs like Twitter, requiring app keys and user tokens [docs/user/authentication.rst:73-84]().
* **OAuth 2**: Supports various flows including Web Application, Mobile, and Backend Application flows [docs/user/authentication.rst:93-101]().

### Custom Handlers
You can implement any proprietary or specialized authentication scheme by subclassing `AuthBase` and overriding `__call__` [src/requests/auth.py:78-82](). Custom handlers are called during request setup and can also attach hooks for additional functionality [docs/user/authentication.rst:138-142]().

For details, see [Custom Authentication](#3.3).

### Community Extensions
The Requests organization maintains several specialized handlers:
* **Kerberos**: `requests-kerberos` [docs/user/authentication.rst:111]()
* **NTLM**: `requests-ntlm` [docs/user/authentication.rst:112]()

Sources: [docs/user/authentication.rst:73-115](), [docs/community/recommended.rst:45-53]()

## Authentication in Sessions

Setting the `auth` attribute on a `Session` object ensures that all requests made through that session use the specified credentials by default [docs/user/authentication.rst:54-56]().

| Authentication Type | Class / Method | Implementation |
| :--- | :--- | :--- |
| **Basic** | `HTTPBasicAuth` | Sets `Authorization` header [src/requests/auth.py:111-113]() |
| **Proxy** | `HTTPProxyAuth` | Sets `Proxy-Authorization` header [src/requests/auth.py:119-121]() |
| **Digest** | `HTTPDigestAuth` | Challenge-response state management [src/requests/auth.py:124-155]() |
| **Custom** | Subclass `AuthBase` | Implement `__call__` [src/requests/auth.py:78]() |

Sources: [src/requests/auth.py:78-155](), [docs/user/authentication.rst:54-56]()

---

# Page: Basic Authentication

# Basic Authentication

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [AUTHORS.rst](AUTHORS.rst)
- [src/requests/auth.py](src/requests/auth.py)
- [src/requests/cookies.py](src/requests/cookies.py)
- [tests/test_lowlevel.py](tests/test_lowlevel.py)
- [tests/test_requests.py](tests/test_requests.py)
- [tests/test_testserver.py](tests/test_testserver.py)
- [tests/test_utils.py](tests/test_utils.py)

</details>



This page documents HTTP Basic Authentication in the Requests library. Basic Authentication is the simplest form of HTTP authentication and is widely supported by web services. For more complex authentication methods like Digest Authentication, see [Digest Authentication](#3.2), or for creating custom authentication handlers, see [Custom Authentication](#3.3).

## Overview

HTTP Basic Authentication involves sending a username and password with each HTTP request. In Requests, this is implemented through the `HTTPBasicAuth` class, though there is also a convenient shorthand syntax available.

```mermaid
graph TD
    subgraph "Authentication_Hierarchy"
        AuthBase["requests.auth.AuthBase"]
        BasicAuth["requests.auth.HTTPBasicAuth"]
        ProxyAuth["requests.auth.HTTPProxyAuth"]
        
        AuthBase -->|"implements"| BasicAuth
        BasicAuth -->|"extends"| ProxyAuth
    end
    
    subgraph "Usage_Methods"
        ExplicitAuth["Explicit_HTTPBasicAuth_Object"]
        TupleAuth["Shorthand_Tuple_('user',_'pass')"]
        NetrcAuth["Automatic_.netrc_fallback"]
        
        ExplicitAuth -->|"creates"| BasicAuth
        TupleAuth -->|"internally_creates"| BasicAuth
        NetrcAuth -->|"falls back to"| BasicAuth
    end
    
    PreparedRequest["requests.models.PreparedRequest"] -->|"uses"| AuthBase
    BasicAuth -->|"adds"| AuthHeader["Authorization_Header"]
    ProxyAuth -->|"adds"| ProxyHeader["Proxy-Authorization_Header"]
```

Sources: [src/requests/auth.py:78-121]()

## How to Use Basic Authentication

There are two main ways to implement Basic Authentication in Requests:

### 1. Using the HTTPBasicAuth Class

The most explicit way is to create an instance of `HTTPBasicAuth` and pass it to the `auth` parameter of a request method or a `Session` object:

```python
from requests.auth import HTTPBasicAuth
response = requests.get(
    'https://httpbin.org/basic-auth/user/pass',
    auth=HTTPBasicAuth('user', 'pass')
)
```

Sources: [src/requests/auth.py:85-98]()

### 2. Using the Shorthand Tuple

For convenience, Requests allows you to simply pass a tuple of `(username, password)` to the `auth` parameter:

```python
response = requests.get(
    'https://httpbin.org/basic-auth/user/pass',
    auth=('user', 'pass')
)
```

This shorthand is equivalent to using the `HTTPBasicAuth` class explicitly.

## How Basic Authentication Works

The authentication flow involves preparing a `PreparedRequest` object and injecting the necessary headers before transmission.

```mermaid
sequenceDiagram
    participant User as "User API (requests.get)"
    participant Session as "requests.sessions.Session"
    participant Auth as "requests.auth.HTTPBasicAuth"
    participant Utils as "requests.auth._basic_auth_str"
    participant Req as "requests.models.PreparedRequest"
    
    User->>Session: get(url, auth=...)
    Session->>Auth: __call__(PreparedRequest)
    Auth->>Utils: _basic_auth_str(username, password)
    Utils->>Utils: b64encode(username:password)
    Utils-->>Auth: "Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ=="
    Auth->>Req: headers['Authorization'] = ...
    Req-->>User: Request ready for transport
```

The process works as follows:

1. The `HTTPBasicAuth` class takes `username` and `password` parameters during initialization [src/requests/auth.py:96-98]().
2. When a request is prepared, the `__call__` method is executed [src/requests/auth.py:111-113]().
3. Inside this method, it sets the `Authorization` header using the `_basic_auth_str` function [src/requests/auth.py:112-112]().
4. This function:
   - Handles legacy non-string types with a `DeprecationWarning` [src/requests/auth.py:44-63]().
   - Encodes `str` inputs to `latin1` bytes [src/requests/auth.py:65-69]().
   - Joins them with a colon (`:`), applies `b64encode`, and prefixes with `Basic ` [src/requests/auth.py:71-73]().

Sources: [src/requests/auth.py:34-75](), [src/requests/auth.py:111-113]()

## Technical Implementation

The `HTTPBasicAuth` class inherits from `AuthBase` [src/requests/auth.py:85-85](), which defines the interface for authentication handlers.

| Class/Function | Responsibility |
| :--- | :--- |
| `AuthBase` | Abstract base class requiring implementation of `__call__` [src/requests/auth.py:78-82](). |
| `HTTPBasicAuth` | Manages credentials and injects `Authorization` header [src/requests/auth.py:85-113](). |
| `_basic_auth_str` | Internal utility for RFC 7617 compliant header string generation [src/requests/auth.py:34-75](). |
| `HTTPProxyAuth` | Subclass of `HTTPBasicAuth` that targets the `Proxy-Authorization` header [src/requests/auth.py:116-121](). |

Sources: [src/requests/auth.py:78-121]()

## Automatic netrc Authentication

If no authentication method is explicitly provided with the `auth` parameter, Requests will automatically attempt to find credentials in the user's `.netrc` file for the request URL's hostname.

The internal function `get_netrc_auth` (defined in `requests.utils`) is used to parse these files and retrieve credentials [tests/test_utils.py:16-26](). It is designed to ignore empty default credentials [tests/test_utils.py:173-182]() and is protected against malicious URL parsing [tests/test_utils.py:165-171]().

Tests confirm that `get_netrc_auth` correctly identifies machines and handles environment variable overrides for the `NETRC` path [tests/test_utils.py:157-163]().

Sources: [tests/test_utils.py:16-26](), [tests/test_utils.py:156-182]()

## HTTP Proxy Authentication

For authenticating with HTTP proxies, Requests provides the `HTTPProxyAuth` class. It inherits from `HTTPBasicAuth` but overrides the `__call__` method to populate the `Proxy-Authorization` header instead [src/requests/auth.py:116-121]().

```python
from requests.auth import HTTPProxyAuth
proxies = {'http': 'http://10.10.1.10:3128'}
requests.get('http://example.org', proxies=proxies, auth=HTTPProxyAuth('user', 'pass'))
```

Sources: [src/requests/auth.py:116-121]()

## Technical Considerations

### Character Encoding
Requests encodes the username and password using `latin1` before Base64 encoding [src/requests/auth.py:65-69](). This follows historical HTTP standards.

### Deprecation of Non-String Types
The library currently issues a `DeprecationWarning` if `username` or `password` are not `basestring` types (e.g., integers). This support is scheduled for removal in version 3.0.0 [src/requests/auth.py:44-63]().

```mermaid
graph LR
    Input["Input_(str/bytes/int)"] --> Guard{"Is_basestring?"}
    Guard -- No --> Warn["Issue_DeprecationWarning"]
    Warn --> Convert["Cast_to_str()"]
    Guard -- Yes --> TypeCheck{"Is_str?"}
    Convert --> TypeCheck
    TypeCheck -- Yes --> Latin["Encode_latin1"]
    TypeCheck -- No --> Join["Join_with_':'"]
    Latin --> Join
    Join --> B64["b64encode"]
    B64 --> Final["Prefix_'Basic_'"]
```

Sources: [src/requests/auth.py:34-75]()

---

# Page: Digest Authentication

# Digest Authentication

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [AUTHORS.rst](AUTHORS.rst)
- [src/requests/auth.py](src/requests/auth.py)
- [src/requests/cookies.py](src/requests/cookies.py)
- [tests/test_lowlevel.py](tests/test_lowlevel.py)
- [tests/test_requests.py](tests/test_requests.py)
- [tests/test_testserver.py](tests/test_testserver.py)
- [tests/test_utils.py](tests/test_utils.py)

</details>



This document describes HTTP Digest Authentication support in the Requests library. Digest Authentication is a more secure alternative to Basic Authentication as it avoids transmitting passwords in plain text over the network by using a challenge-response flow.

## Overview

Digest Authentication is a mechanism where the server challenges the client, and the client proves knowledge of a password through cryptographic hashing. Requests implements this via the `HTTPDigestAuth` class [src/requests/auth.py:124-124]().

Key characteristics:
- **Hashing Algorithms**: Uses `hashlib` for various hashing algorithms (MD5, SHA-256, SHA-512) [src/requests/auth.py:174-205]().
- **Replay Protection**: Protects against replay attacks using a `nonce_count` [src/requests/auth.py:131-131]().
- **Thread Safety**: Maintains state using thread-local storage to ensure thread safety across concurrent requests [src/requests/auth.py:129-129](), [src/requests/auth.py:145-145]().
- **Automatic Handling**: Handles 401 challenges automatically via a response hook mechanism [src/requests/auth.py:285-303]().

Sources: [src/requests/auth.py:124-314]()

## Basic Usage

To use Digest Authentication, instantiate `HTTPDigestAuth` with credentials and pass it to the `auth` parameter of a request method. The class supports both `str` and `bytes` for credentials [src/requests/auth.py:137-141]().

```python
from requests.auth import HTTPDigestAuth
import requests

url = 'https://httpbin.org/digest-auth/auth/user/pass'
requests.get(url, auth=HTTPDigestAuth('user', 'pass'))
```

Sources: [src/requests/auth.py:124-143](), [tests/test_requests.py:85-85]()

## Authentication Flow

Digest Authentication involves a specific challenge-response cycle. The initial request usually fails with a `401 Unauthorized`, providing the parameters needed for the digest calculation in the `WWW-Authenticate` header.

### Challenge-Response Sequence
The following diagram illustrates the interaction between the library components and the remote server during a Digest challenge.

```mermaid
sequenceDiagram
    participant App as "Application Code"
    participant Session as "requests.Session"
    participant Auth as "HTTPDigestAuth"
    participant Server as "Remote HTTP Server"

    App->>Session: "get(url, auth=HTTPDigestAuth)"
    Session->>Server: "Request (No Authorization header)"
    Server-->>Session: "401 Unauthorized (WWW-Authenticate: Digest ...)"
    Session->>Auth: "handle_401(Response)"
    Auth->>Auth: "build_digest_header(method, url)"
    Auth-->>Session: "PreparedRequest (with Authorization header)"
    Session->>Server: "Request (with Digest Authorization)"
    Server-->>App: "200 OK"
```

Sources: [src/requests/auth.py:241-283](), [src/requests/auth.py:285-303](), [tests/test_lowlevel.py:152-174]()

## Implementation Architecture

The following diagram maps the logical components of the Digest Auth system to the specific classes and methods in the `requests.auth` module.

### Code Entity Mapping
```mermaid
classDiagram
    class AuthBase {
        <<interface>>
        +__call__(r: PreparedRequest)
    }
    class HTTPDigestAuth {
        +username: str
        +password: str
        +_thread_local: threading.local
        +__call__(r: PreparedRequest)
        +handle_401(r: Response)
        +build_digest_header(method: str, url: str)
        +init_per_thread_state()
    }
    class PreparedRequest {
        +headers: dict
        +url: str
    }
    class Response {
        +status_code: int
        +headers: dict
        +request: PreparedRequest
    }
    
    AuthBase <|-- HTTPDigestAuth : "inherits"
    HTTPDigestAuth ..> PreparedRequest : "modifies/prepares"
    HTTPDigestAuth ..> Response : "consumes challenge from"
    HTTPDigestAuth ..> "threading.local" : "uses for state"
```

Sources: [src/requests/auth.py:78-83](), [src/requests/auth.py:124-156](), [src/requests/auth.py:241-314]()

## Thread Safety

`HTTPDigestAuth` utilizes `threading.local` to maintain state (like nonces and counts) across multiple requests within the same thread without cross-talk in concurrent environments [src/requests/auth.py:145-145]().

```mermaid
graph TD
    subgraph "Thread_Context_A"
        StateA["HTTPDigestAuth._thread_local"]
        StateA --> NonceA["last_nonce"]
        StateA --> CountA["nonce_count"]
    end
    
    subgraph "Thread_Context_B"
        StateB["HTTPDigestAuth._thread_local"]
        StateB --> NonceB["last_nonce"]
        StateB --> CountB["nonce_count"]
    end

    AuthObj["HTTPDigestAuth_Instance"] --> StateA
    AuthObj --> StateB
```

The `init_per_thread_state` method ensures that the `_thread_local` storage is populated for the current execution context [src/requests/auth.py:147-156]().

Sources: [src/requests/auth.py:129-132](), [src/requests/auth.py:145-156]()

## Digest Header Construction

The `build_digest_header` function performs the calculation of the cryptographic response. It parses the server's challenge using `parse_dict_header` [src/requests/auth.py:22-22](), [src/requests/auth.py:162-166]() and computes the `response` field.

### Supported Algorithms
| Algorithm | Hashing Implementation | Source |
| :--- | :--- | :--- |
| **MD5** | `hashlib.md5(..., usedforsecurity=False)` | [src/requests/auth.py:179-179]() |
| **SHA-256** | `hashlib.sha256(..., usedforsecurity=False)` | [src/requests/auth.py:195-195]() |
| **SHA-512** | `hashlib.sha512(..., usedforsecurity=False)` | [src/requests/auth.py:203-203]() |

The `KD(s, d)` function is used internally to represent `H(s:d)` as defined in RFC 2617 [src/requests/auth.py:210-211]().

Sources: [src/requests/auth.py:157-239]()

## Handling 401 Unauthorized

The core logic for handling the challenge-response cycle resides in `handle_401`. When a request returns a 401, this method intercepts the response, calculates the digest, and triggers a retry [src/requests/auth.py:241-241]().

1. **Check for Challenge**: Verifies if `WWW-Authenticate` contains "digest" (case-insensitive) [src/requests/auth.py:252-252]().
2. **State Management**: Updates `last_nonce` and increments `nonce_count`. If the nonce has changed, the count is reset to 1 [src/requests/auth.py:265-270]().
3. **Re-sending**: Uses `r.connection.send` to dispatch the new `PreparedRequest` containing the generated credentials [src/requests/auth.py:279-281]().
4. **Infinite Loop Protection**: Tracks `num_401_calls` to prevent getting stuck in a challenge loop [src/requests/auth.py:243-247]().

The state of `num_401_calls` is correctly reset after successful authentication or redirects to ensure consecutive challenges can be handled [tests/test_lowlevel.py:127-132]().

Sources: [src/requests/auth.py:241-283](), [tests/test_lowlevel.py:127-190]()

## Security Considerations

- **HTTPS Recommendation**: Digest Auth does not encrypt the message body; it only protects the password. It should be used over TLS to prevent eavesdropping on the challenge parameters.
- **FIPS Compliance**: Requests uses `usedforsecurity=False` in its `hashlib` calls to allow operation in FIPS-compliant environments where these algorithms are generally restricted for high-security use but required for protocol compatibility [src/requests/auth.py:179-179](), [src/requests/auth.py:195-195](), [src/requests/auth.py:203-203]().
- **QOP Support**: The "auth-int" (integrity) quality of protection is not fully implemented; only "auth" is supported for the `qop` parameter [src/requests/auth.py:221-232]().

Sources: [src/requests/auth.py:174-205](), [src/requests/auth.py:214-232]()

---

# Page: Custom Authentication

# Custom Authentication

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [docs/community/recommended.rst](docs/community/recommended.rst)
- [docs/user/authentication.rst](docs/user/authentication.rst)
- [src/requests/auth.py](src/requests/auth.py)
- [src/requests/cookies.py](src/requests/cookies.py)

</details>



This page explains how to create custom authentication handlers in the Requests library. Custom authentication allows you to implement authentication schemes not natively supported by Requests by extending the `AuthBase` class.

## How Authentication Works in Requests

Authentication in Requests is implemented through authentication handlers that modify requests before they are sent to the transport layer. When you make a request with the `auth` parameter, the authentication handler is called during request setup. Specifically, the handler is invoked on a `PreparedRequest` object [src/requests/auth.py:81-82]().

### Request-Auth Data Flow

The following diagram illustrates how a custom authentication handler interacts with the request lifecycle, transforming a user-provided request into a prepared one ready for transport.

```mermaid
sequenceDiagram
    participant "User Code" as User
    participant "requests.api" as API
    participant "requests.models.PreparedRequest" as PreparedRequest
    participant "requests.auth.AuthBase" as AuthHandler
    participant "requests.adapters.HTTPAdapter" as Adapter
    
    User->>API: "get(url, auth=CustomAuth())"
    API->>PreparedRequest: "prepare_auth(auth)"
    PreparedRequest->>AuthHandler: "__call__(PreparedRequest)"
    Note over AuthHandler: "Modify headers or body"
    AuthHandler-->>PreparedRequest: "return PreparedRequest"
    PreparedRequest->>Adapter: "send(PreparedRequest)"
    Adapter->>User: "Response"
```

Sources: [src/requests/auth.py:78-82](), [docs/user/authentication.rst:138-142]()

### Authentication Class Hierarchy

Requests provides a base class `AuthBase` which defines the interface for all authentication implementations. The library includes built-in implementations for Basic and Digest authentication.

```mermaid
classDiagram
    class AuthBase {
        <<interface>>
        +__call__(r: PreparedRequest) PreparedRequest
    }
    class HTTPBasicAuth {
        +username: bytes | str
        +password: bytes | str
        +__init__(username, password)
        +__call__(r: PreparedRequest) PreparedRequest
    }
    class HTTPDigestAuth {
        +username: bytes | str
        +password: bytes | str
        -_thread_local: local
        +__init__(username, password)
        +__call__(r: PreparedRequest) PreparedRequest
        +handle_401(r: Response) Response
    }
    class HTTPProxyAuth {
        +__call__(r: PreparedRequest) PreparedRequest
    }
    class MyCustomAuth {
        +__call__(r: PreparedRequest) PreparedRequest
    }
    
    AuthBase <|-- HTTPBasicAuth
    AuthBase <|-- HTTPDigestAuth
    HTTPBasicAuth <|-- HTTPProxyAuth
    AuthBase <|-- MyCustomAuth
```

Sources: [src/requests/auth.py:78-126](), [docs/user/authentication.rst:125-132]()

## Creating a Custom Authentication Handler

To create a custom authentication handler, you must subclass `AuthBase` and implement the `__call__` method [src/requests/auth.py:78-82]().

### The AuthBase Interface

The `AuthBase` class is a simple interface located in `requests.auth`.

[src/requests/auth.py:78-82]()
```python
class AuthBase:
    """Base class that all auth implementations derive from"""

    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        raise NotImplementedError("Auth hooks must be callable.")
```

### Implementation Steps

1.  **Subclass `AuthBase`**: Inherit from the base class [src/requests/auth.py:78-82]().
2.  **Implement `__init__`**: Store credentials or configuration [src/requests/auth.py:96-98]().
3.  **Implement `__call__`**: Modify the `PreparedRequest` object (usually its `headers` attribute) and return it [src/requests/auth.py:111-113]().

Sources: [src/requests/auth.py:78-113](), [docs/user/authentication.rst:125-132]()

## Example: Header-Based Authentication

Many modern APIs use a custom header for authentication. This is the most straightforward implementation.

```python
import requests
from requests.auth import AuthBase

class APIKeyAuth(AuthBase):
    """Attaches API Key Authentication to the given Request object."""
    def __init__(self, api_key):
        self.api_key = api_key

    def __call__(self, r):
        # r is a PreparedRequest object
        r.headers['X-API-Key'] = self.api_key
        return r

# Usage
requests.get('https://httpbin.org/get', auth=APIKeyAuth('secret-token'))
```

Sources: [src/requests/auth.py:111-114](), [docs/user/authentication.rst:129-136]()

## Example: Advanced Challenge-Response

Some authentication schemes, like HTTP Digest, require a challenge-response flow. This involves using event hooks to intercept `401 Unauthorized` responses and retry the request with the correct credentials.

The `HTTPDigestAuth` implementation uses this pattern. It registers a `response` hook to handle the authentication challenge [src/requests/auth.py:124-146]().

```python
    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        # ... (setup logic)
        r.register_hook("response", self.handle_401)
        return r
```

The hook function then checks the status code and potentially retries the request. The state for these multi-step authentications is often stored in per-thread local storage to ensure thread safety [src/requests/auth.py:144-146]().

Sources: [src/requests/auth.py:124-155](), [docs/user/authentication.rst:138-142]()

## Integration with Third-Party Libraries

The Requests ecosystem includes several specialized authentication handlers maintained outside the core library:

| Provider | Library | Purpose |
| :--- | :--- | :--- |
| OAuth 1.0/2.0 | `requests-oauthlib` | Automated OAuth flow handling [docs/community/recommended.rst:45-53]() |
| Kerberos | `requests-kerberos` | Kerberos/GSSAPI authentication [docs/user/authentication.rst:111]() |
| NTLM | `requests-ntlm` | Microsoft NTLM authentication [docs/user/authentication.rst:112]() |

Sources: [docs/user/authentication.rst:73-114](), [docs/community/recommended.rst:45-53]()

## Best Practices

1.  **Thread Safety**: If your auth handler maintains state (like `HTTPDigestAuth`), use `threading.local()` to ensure it is thread-safe [src/requests/auth.py:144-146]().
2.  **Native Strings**: When adding headers, ensure keys and values are native strings to avoid encoding issues. Requests uses `to_native_string` internally for this [src/requests/auth.py:19-22]().
3.  **Use PreparedRequests**: Remember that the `__call__` method receives a `PreparedRequest`, not a standard `Request`. This means the URL and body are already finalized [src/requests/auth.py:81-82]().
4.  **Proxy Auth**: If implementing proxy authentication, use the `Proxy-Authorization` header instead of `Authorization`. See `HTTPProxyAuth` for a reference implementation [src/requests/auth.py:116-121]().
5.  **Basic Auth Formatting**: For standard Basic Auth, use the internal `_basic_auth_str` helper which handles `latin1` encoding and `base64` formatting [src/requests/auth.py:34-75]().

Sources: [src/requests/auth.py:19-155](), [src/requests/cookies.py:45-47]()

---

# Page: Advanced Usage

# Advanced Usage

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [AUTHORS.rst](AUTHORS.rst)
- [docs/api.rst](docs/api.rst)
- [docs/user/advanced.rst](docs/user/advanced.rst)
- [docs/user/quickstart.rst](docs/user/quickstart.rst)
- [tests/test_requests.py](tests/test_requests.py)

</details>



This page documents advanced features of the Requests library. These features provide control over HTTP request behavior, enable performance optimizations through connection reuse, and support complex workflows like request modification, multipart uploads, and custom HTTP methods.

## Topics Overview

Advanced topics are organized across this page and child sections:

| Section | Topic | Purpose |
|---------|-------|---------|
| This Page | Session objects, prepared requests, HTTP verbs | Core advanced patterns |
| [SSL Verification](#4.1) | SSL Verification | Certificate verification, CA bundles, client certificates |
| [Streaming and Chunks](#4.2) | Streaming and Chunks | Response streaming, chunked encoding, large file handling |
| [Proxies and Tunneling](#4.3) | Proxies and Tunneling | Proxy configuration, SOCKS support, environment variables |
| [Event Hooks](#4.4) | Event Hooks | Request/response interception and modification |
| [Timeout Configuration](#4.5) | Timeout Configuration | Connect and read timeouts, timing behavior |

## Session Objects

The `Session` class ([requests/sessions.py:355-360]()) provides persistent state across HTTP requests. Sessions maintain cookies via `RequestsCookieJar` ([requests/cookies.py:162-167]()), reuse TCP connections through `HTTPAdapter` ([requests/adapters.py:83-100]()) connection pools, and persist configuration like headers and authentication.

**Session State and Connection Pooling**

```mermaid
graph TB
    subgraph "requests.sessions.Session"
        [Session] --> headers["headers: CaseInsensitiveDict"]
        [Session] --> cookies["cookies: RequestsCookieJar"]
        [Session] --> auth["auth: AuthBase or tuple"]
        [Session] --> adapters["adapters: OrderedDict"]
    end
    
    subgraph "requests.adapters.HTTPAdapter"
        adapters --> [HTTPAdapter]
        [HTTPAdapter] --> poolmanager["poolmanager: urllib3.PoolManager"]
        poolmanager --> conn1["HTTPConnection 1"]
        poolmanager --> conn2["HTTPConnection 2"]
        poolmanager --> conn3["HTTPConnection N"]
    end
    
    [Session] --> |"request() calls"| send["send(PreparedRequest)"]
    send --> |"selects adapter"| [HTTPAdapter]
    [HTTPAdapter] --> |"reuses connections"| poolmanager
```

**Cookie Persistence**

Cookies set by the server persist across requests within a `Session` [docs/user/advanced.rst:24-30]():

```python
s = requests.Session()
s.get('https://httpbin.org/cookies/set/sessioncookie/123456789')
r = s.get('https://httpbin.org/cookies')
# Session maintains the cookie across requests
```

Sources: [docs/user/advanced.rst:10-30](), [requests/sessions.py:355-360]()

**Default Request Parameters**

Session-level parameters apply to all requests unless overridden [docs/user/advanced.rst:44-46]():

```python
s = requests.Session()
s.auth = ('user', 'pass')
s.headers.update({'x-test': 'true'})

# Both session headers and request-specific headers are sent
s.get('https://httpbin.org/headers', headers={'x-test2': 'true'})
```

Method-level parameters override session parameters but do not persist [docs/user/advanced.rst:48-51]():

```python
s = requests.Session()
r = s.get('https://httpbin.org/cookies', cookies={'from-my': 'browser'})
# First request includes the cookie
r = s.get('https://httpbin.org/cookies')
# Second request does not include the cookie
```

Sources: [docs/user/advanced.rst:33-60]()

**Context Manager Usage**

Sessions implement the context manager protocol and should be closed to release connection pool resources [docs/user/advanced.rst:67-73]():

```python
with requests.Session() as s:
    s.get('https://httpbin.org/cookies/set/sessioncookie/123456789')
# Session is closed automatically via __exit__
```

Sources: [docs/user/advanced.rst:67-73](), [requests/sessions.py:424-428]()

**Removing Session-Level Values**

To omit a session-level parameter from a specific request, set it to `None` [docs/user/advanced.rst:78-80]():

```python
s = requests.Session()
s.headers.update({'custom-header': 'value'})
# Remove the header for this request only
s.get('https://httpbin.org/get', headers={'custom-header': None})
```

Sources: [docs/user/advanced.rst:76-80]()

## Request and Response Objects

API calls create a `Request` object ([requests/models.py:202-230]()) which is prepared into a `PreparedRequest` ([requests/models.py:294-311]()) before transmission. The server returns a `Response` ([requests/models.py:613-625]()) object that contains both the response data and the original `PreparedRequest` [docs/user/advanced.rst:90-96]().

**Request Lifecycle**

```mermaid
sequenceDiagram
    participant API as "requests.get()"
    participant Req as "requests.models.Request"
    participant Prep as "requests.models.PreparedRequest"
    participant Adapter as "requests.adapters.HTTPAdapter"
    participant Response as "requests.models.Response"
    
    API->>Req: Create Request object
    Req->>Prep: Request.prepare()
    Prep->>Adapter: Session.send(PreparedRequest)
    Adapter->>Adapter: urllib3 HTTP call
    Adapter->>Response: Build Response object
    Response->>API: Return Response
    
    note over Response: Response.request attribute<br>contains PreparedRequest
```

**Accessing Request and Response Headers**

The `Response` object provides access to both response headers and the original request headers [docs/user/advanced.rst:100-118]():

```python
r = requests.get('https://en.wikipedia.org/wiki/Monty_Python')

# Server response headers
r.headers
# {'content-length': '56170', 'x-content-type-options': 'nosniff', ...}

# Original request headers
r.request.headers
# {'Accept-Encoding': 'identity, deflate, compress, gzip', ...}
```

Sources: [docs/user/advanced.rst:87-118](), [requests/models.py:202-625]()

## Prepared Requests

A `PreparedRequest` ([requests/models.py:294-311]()) is the final request representation before transmission. It allows modification of request body, headers, and other attributes before sending [docs/user/advanced.rst:126-129]().

**Preparation Methods**

```mermaid
graph TB
    subgraph "Request Preparation"
        [Request] --> |"Request.prepare()"| [PreparedRequest]
        [Session] --> |"Session.prepare_request()"| [PreparedRequest]
    end
    
    [PreparedRequest] --> |"No session state"| NoState["No cookies, auth, etc."]
    [PreparedRequest] --> |"Includes session state"| WithState["Cookies, auth, headers"]
    
    [PreparedRequest] --> Modify["Modify body/headers"]
    Modify --> Send["Session.send()"]
```

**Direct Preparation (No Session State)**

`Request.prepare()` ([requests/models.py:265-285]()) creates a `PreparedRequest` without applying session state [docs/user/advanced.rst:130-149]():

```python
from requests import Request, Session

s = Session()
req = Request('POST', url, data=data, headers=headers)
prepped = req.prepare()

# Modify the prepared request
prepped.body = 'No, I want exactly this as the body.'
del prepped.headers['Content-Type']

resp = s.send(prepped)
```

Sources: [docs/user/advanced.rst:120-156](), [requests/models.py:265-285]()

**Session-Based Preparation (With Session State)**

`Session.prepare_request()` ([requests/sessions.py:441-450]()) applies session-level cookies, authentication, and headers [docs/user/advanced.rst:163-165]():

```python
from requests import Request, Session

s = Session()
req = Request('GET', url, data=data, headers=headers)
prepped = s.prepare_request(req)

# Modify the prepared request
prepped.body = 'Seriously, send exactly these bytes.'
prepped.headers['Keep-Dead'] = 'parrot'

resp = s.send(prepped)
```

Sources: [docs/user/advanced.rst:158-188](), [requests/sessions.py:441-450]()

**Environment Settings**

Prepared requests do not automatically include environment-based settings like `REQUESTS_CA_BUNDLE`. Use `Session.merge_environment_settings()` ([requests/sessions.py:711-715]()) to apply them [docs/user/advanced.rst:190-200]():

```python
from requests import Request, Session

s = Session()
req = Request('GET', url)
prepped = s.prepare_request(req)

# Merge environment settings (proxies, verify, cert, stream)
settings = s.merge_environment_settings(prepped.url, {}, None, None, None)
resp = s.send(prepped, **settings)
```

Sources: [docs/user/advanced.rst:190-207](), [requests/sessions.py:711-715]()

For more details on security settings, see [SSL Verification](#4.1).

## Keep-Alive and Connection Pooling

HTTP Keep-Alive and connection pooling are automatic within a `Session` via urllib3's `PoolManager` ([requests/adapters.py:155-165]()). TCP connections are reused for subsequent requests to the same host [docs/user/advanced.rst:15-18]().

**Connection Reuse Mechanism**

```mermaid
graph TB
    subgraph "Session Connection Pool"
        [Session] --> [HTTPAdapter]
        [HTTPAdapter] --> [PoolManager]
        [PoolManager] --> Conn1["HTTPConnection<br>host: api.github.com"]
        [PoolManager] --> Conn2["HTTPConnection<br>host: httpbin.org"]
    end
    
    Req1["s.get('https://api.github.com/user')"] --> |"uses"| Conn1
    Req2["s.get('https://api.github.com/repos')"] --> |"reuses"| Conn1
    Req3["s.get('https://httpbin.org/get')"] --> |"uses"| Conn2
    
    Conn1 --> |"released when"| Release["Response.content read or<br>Response.close() called"]
```

**Connection Release**

Connections return to the pool only after response content is fully consumed:

- **Immediate release**: With `stream=False` (default), content is read immediately.
- **Manual release**: With `stream=True`, read `Response.content` or call `Response.close()` [docs/user/quickstart.rst:170-173]().
- **Context manager**: Use `with` statement on the response for automatic cleanup [docs/user/quickstart.rst:185-188]().

```python
# Best practice for streaming
with requests.get('https://httpbin.org/get', stream=True) as r:
    # Process response
    pass
# Connection automatically released
```

Sources: [docs/user/advanced.rst:335-346](), [docs/user/quickstart.rst:170-188](), [requests/adapters.py:155-165]()

## Streaming Uploads

File-like objects provided to the `data` parameter are streamed without loading the entire file into memory [docs/user/advanced.rst:348-350]().

**Streaming Upload Process**

```mermaid
graph LR
    FileObj["File Object<br>(opened in 'rb' mode)"] --> |"data parameter"| [PreparedRequest]
    [PreparedRequest] --> |"chunks read"| [HTTPAdapter]
    [HTTPAdapter] --> |"sent via urllib3"| Server["Server"]
```

**Basic Upload**

```python
with open('massive-body', 'rb') as f:
    requests.post('http://some.url/streamed', data=f)
```

Files must be opened in binary mode (`'rb'`) to ensure correct `Content-Length` header calculation [docs/user/advanced.rst:358-364]().

Sources: [docs/user/advanced.rst:348-364]()

## Chunk-Encoded Requests

Generators or iterators without a `__len__()` method provided to the `data` parameter trigger `Transfer-Encoding: chunked` in the outgoing request [docs/user/advanced.rst:368-372]().

**Chunked Request Encoding**

```mermaid
graph LR
    Generator["Generator/Iterator"] --> |"data parameter"| [PreparedRequest]
    [PreparedRequest] --> |"Transfer-Encoding: chunked"| Server["Server"]
    
    Generator -.-> NoLen["No __len__() method"]
    NoLen -.-> Chunked["Uses chunked encoding"]
```

**Sending Chunked Data**

```python
def gen():
    yield 'hi'
    yield 'there'

requests.post('http://some.url/chunked', data=gen())
```

Sources: [docs/user/advanced.rst:368-380](), [tests/test_requests.py:129-138]()

## POST Multiple Multipart-Encoded Files

The `files` parameter accepts a list of tuples for multipart/form-data encoding, allowing multiple files under the same form field name [docs/user/advanced.rst:410-419]().

**Multipart File Upload Structure**

```mermaid
graph TB
    FilesParam["files parameter"] --> |"list of tuples"| Encoder["requests.models.RequestEncodingMixin"]
    Encoder --> |"creates"| MultipartBody["multipart/form-data body"]
    
    MultipartBody --> Part1["--boundary<br>Content-Disposition: form-data; name=images<br>Content-Type: image/png<br><br>file1 data"]
    MultipartBody --> Part2["--boundary<br>Content-Disposition: form-data; name=images<br>Content-Type: image/png<br><br>file2 data"]
```

**Sending Multiple Files**

```python
url = 'https://httpbin.org/post'
multiple_files = [
    ('images', ('foo.png', open('foo.png', 'rb'), 'image/png')),
    ('images', ('bar.png', open('bar.png', 'rb'), 'image/png'))
]
r = requests.post(url, files=multiple_files)
```

Sources: [docs/user/advanced.rst:390-419]()

## Compliance

### Encodings

```mermaid
flowchart TD
    subgraph "Response Encoding Detection"
        R["Response"] --> |"check"| H{"HTTP Header<br>Has Charset?"}
        H -->|"Yes"| UH["Use Header Charset"]
        H -->|"No"| A{"Content-Type<br>contains 'text'?"}
        A -->|"Yes"| D["Default to ISO-8859-1<br>(RFC 2616)"]
        A -->|"No"| G["Guess using<br>charset_normalizer"]
    end
```

Requests determines the encoding for text responses using `get_encoding_from_headers` ([requests/utils.py:87]()) and `get_encodings_from_content` ([requests/utils.py:86]()). If no charset is found in the headers, it defaults to ISO-8859-1 for text content types [docs/user/quickstart.rst:99-102]().

Sources: [docs/user/quickstart.rst:99-132](), [docs/api.rst:86-88]()

### HTTP Verbs

Requests supports all standard HTTP methods [docs/api.rst:16-26]():

| Method | Purpose | Idempotent | Request Body | 
|--------|---------|------------|--------------|
| `get` | Retrieve resources | Yes | No |
| `head` | Headers only | Yes | No |
| `options` | Discover supported methods | Yes | No |
| `post` | Create resources | No | Yes |
| `put` | Update resources | Yes | Yes |
| `patch` | Partial update | No | Yes |
| `delete` | Delete resources | Yes | Optional |

Sources: [docs/api.rst:16-26](), [docs/user/quickstart.rst:32-49]()

---

# Page: SSL Verification

# SSL Verification

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [AUTHORS.rst](AUTHORS.rst)
- [docs/api.rst](docs/api.rst)
- [docs/user/advanced.rst](docs/user/advanced.rst)
- [docs/user/quickstart.rst](docs/user/quickstart.rst)
- [src/requests/adapters.py](src/requests/adapters.py)
- [src/requests/certs.py](src/requests/certs.py)
- [tests/test_adapters.py](tests/test_adapters.py)
- [tests/test_requests.py](tests/test_requests.py)

</details>



This document explains how SSL certificate verification works in the Requests library, including configuration options, security implications, and internal implementation. SSL verification is a critical security feature that ensures you're connecting to legitimate servers by validating their SSL/TLS certificates.

## Overview

By default, Requests verifies SSL certificates for HTTPS requests, similar to web browsers. This verification protects against man-in-the-middle attacks by confirming that the server's certificate is valid, signed by a trusted Certificate Authority (CA), and matches the requested hostname.

```python
import requests

# This will verify the certificate
response = requests.get('https://github.com')

# This will raise an SSLError for an invalid certificate
# (e.g., hostname mismatch or expired certificate)
```

Sources: [docs/user/advanced.rst:213-224](), [docs/user/quickstart.rst:32-33]()

## Verification Configuration Options

Requests provides several ways to configure SSL certificate verification:

Title: SSL Verification Logic Flow
```mermaid
flowchart TD
    A["SSL Verification Options"] --> B["Default Behavior"]
    A --> C["Custom CA Bundle"]
    A --> D["Disable Verification"]
    A --> E["Environment Variables"]
    
    B --> B1["Use certifi.where() CA certificates"]
    B --> B2["Verify hostname & certificate validity"]
    
    C --> C1["Specify custom CA file<br>verify='/path/to/ca_bundle'"]
    C --> C2["Specify CA directory<br>verify='/path/to/ca_dir'"]
    
    D --> D1["Set verify=False"]
    D --> D2["WARNING: Security risk!"]
    
    E --> E1["REQUESTS_CA_BUNDLE"]
    E --> E2["CURL_CA_BUNDLE (fallback)"]
```

Sources: [docs/user/advanced.rst:226-252](), [src/requests/certs.py:15-18]()

### Default Behavior

By default, `verify` is set to `True`, which means:
- Requests will verify the server's certificate against the CA certificates provided by the `certifi` package. [src/requests/certs.py:7-15]()
- Certificate must be valid (not expired, trusted chain, etc.).
- Hostname must match the certificate's subject.

Sources: [docs/user/advanced.rst:213-225](), [docs/user/advanced.rst:252](), [src/requests/certs.py:7-15]()

### Custom CA Bundle

You can specify a custom CA bundle for verification. This is useful for internal networks or private CAs.

```python
# Using a specific CA bundle file
response = requests.get('https://github.com', verify='/path/to/ca_bundle')

# Set for an entire session
session = requests.Session()
session.verify = '/path/to/ca_bundle'
```

If you specify a directory instead of a file, the directory must have been processed using the `c_rehash` utility supplied with OpenSSL.

Sources: [docs/user/advanced.rst:226-236](), [docs/user/advanced.rst:33-41]()

### Environment Variables

Requests also checks these environment variables for CA bundle paths:
- `REQUESTS_CA_BUNDLE` - Primary environment variable.
- `CURL_CA_BUNDLE` - Used as fallback if `REQUESTS_CA_BUNDLE` is not set.

**Note**: If you are using `PreparedRequest` objects directly via `Session.send()`, environment variables like `REQUESTS_CA_BUNDLE` are not automatically merged into the request context. You must merge them manually using `requests.utils.merge_setting()`. [docs/user/advanced.rst:190-202]()

Sources: [docs/user/advanced.rst:190-202](), [docs/user/advanced.rst:238-239]()

### Disabling Verification

You can disable verification entirely by passing `verify=False`:

```python
response = requests.get('https://example.com', verify=False)
```

**Warning**: When `verify=False`, Requests will accept any TLS certificate presented by the server, ignore hostname mismatches, and ignore expired certificates. This makes your application vulnerable to man-in-the-middle attacks.

Sources: [docs/user/advanced.rst:241-252]()

## Internal Verification Workflow

The following diagram shows how SSL verification settings flow from the high-level API to the transport layer, specifically mapping user-facing parameters to the internal `_urllib3_request_context` function within the `HTTPAdapter`.

Title: SSL Data Flow to Transport Layer
```mermaid
sequenceDiagram
    participant User as "User Code"
    participant Session as "requests.sessions.Session"
    participant Adapter as "requests.adapters.HTTPAdapter"
    participant Context as "requests.adapters._urllib3_request_context"
    participant PM as "urllib3.poolmanager.PoolManager"
    
    User->>+Session: requests.get(url, verify=value, cert=cert_val)
    Session->>+Adapter: send(request, verify=value, cert=cert_val)
    
    Adapter->>+Context: _urllib3_request_context(request, verify, cert)
    
    Note over Context: Processes verify (bool/str)
    Note over Context: Processes client_cert (tuple/str)
    
    alt verify is False
        Context-->>Adapter: pool_kwargs["cert_reqs"] = "CERT_NONE"
    else verify is File Path
        Context-->>Adapter: pool_kwargs["ca_certs"] = verify
    else verify is Dir Path
        Context-->>Adapter: pool_kwargs["ca_cert_dir"] = verify
    end
    
    Adapter->>+PM: urlopen(...)
    PM-->>-Adapter: response
    Adapter-->>-Session: response
    Session-->>-User: response
```

Sources: [src/requests/adapters.py:85-119](), [src/requests/adapters.py:128-150](), [docs/user/advanced.rst:143-152]()

### Key Components and Code Entities

Title: Mapping Logic to Code Entities
```mermaid
classDiagram
    class HTTPAdapter {
        +send(request, verify, cert)
        +poolmanager: PoolManager
    }
    class _urllib3_request_context {
        +verify: bool|str
        +client_cert: tuple|str
    }
    class Session {
        +verify: bool|str
        +cert: tuple|str
        +send(request)
    }
    class certs {
        +where()
    }

    Session ..> HTTPAdapter : "calls send()"
    HTTPAdapter ..> _urllib3_request_context : "prepares kwargs"
    _urllib3_request_context ..> certs : "uses where() as default"
```

| Component | File | Function/Class | Role |
|-----------|------|----------------|------|
| `HTTPAdapter` | [src/requests/adapters.py:158]() | `HTTPAdapter` | The primary transport adapter that manages `urllib3` connection pools. |
| `Context Helper` | [src/requests/adapters.py:85]() | `_urllib3_request_context` | Internal function that maps Requests SSL parameters to `urllib3` keywords. |
| `certs` | [src/requests/certs.py:15]() | `where()` | Returns the file path to the `certifi` CA bundle. |
| `Session` | [src/requests/sessions.py:355]() | `Session` | Manages persistent settings including `verify` and `cert`. |

Sources: [src/requests/adapters.py:85-119](), [src/requests/adapters.py:158-220](), [src/requests/certs.py:1-18]()

## Client Side Certificates

Requests allows you to provide a client-side certificate for mutual TLS (mTLS) authentication. This can be a single file containing both the certificate and the private key, or a tuple of (certificate file, key file).

```python
# Single file (cert and key combined)
requests.get('https://example.com', cert='/path/client.pem')

# Separate files
requests.get('https://example.com', cert=('/path/client.cert', '/path/client.key'))
```

The `_urllib3_request_context` function handles these inputs by populating `cert_file` and `key_file` in the pool arguments passed to `urllib3`. [src/requests/adapters.py:106-113]()

Sources: [docs/user/advanced.rst:254-277](), [src/requests/adapters.py:106-113]()

## Implementation Detail: `_urllib3_request_context`

The `_urllib3_request_context` function in `src/requests/adapters.py` is responsible for applying SSL settings to the underlying `urllib3` connection parameters.

1. **Verify Parameter**:
   - If `verify` is `False`, it sets `cert_reqs` to `"CERT_NONE"`. [src/requests/adapters.py:98-99]()
   - If `verify` is a string and a file, it sets `ca_certs`. [src/requests/adapters.py:101-102]()
   - If `verify` is a string and a directory, it sets `ca_cert_dir`. [src/requests/adapters.py:103-104]()
2. **Cert Parameter**:
   - If `client_cert` is a tuple of length 2, it maps index 0 to `cert_file` and index 1 to `key_file`. [src/requests/adapters.py:107-109]()
   - Otherwise, it assigns the value to `cert_file`. [src/requests/adapters.py:113]()

Sources: [src/requests/adapters.py:85-119]()

## Security Considerations

1. **CA Bundle Management**: Requests defaults to the bundle provided by `certifi`. For managed environments, developers can override `requests.certs.where()` to point to a system-specific CA bundle. [src/requests/certs.py:7-13]()
2. **Expired Certificates**: Using an expired certificate in a test suite will trigger an `SSLError` unless `verify=False` is used.
3. **Session Persistence**: Settings for `verify` and `cert` can be persisted across requests using a `Session` object. [docs/user/advanced.rst:13-18]()

Sources: [src/requests/certs.py:1-18](), [docs/user/advanced.rst:13-18]()

---

# Page: Streaming and Chunks

# Streaming and Chunks

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [docs/api.rst](docs/api.rst)
- [docs/user/advanced.rst](docs/user/advanced.rst)
- [docs/user/quickstart.rst](docs/user/quickstart.rst)
- [src/requests/models.py](src/requests/models.py)
- [tests/test_lowlevel.py](tests/test_lowlevel.py)
- [tests/test_testserver.py](tests/test_testserver.py)
- [tests/test_utils.py](tests/test_utils.py)

</details>



This page explains how to work with streaming responses and chunk-encoded data in the `requests` library. Streaming enables you to process response data incrementally rather than loading it entirely into memory at once. This is especially useful for handling large downloads efficiently or processing data from streaming APIs in real-time.

## Understanding Streaming in Requests

By default, when you make a request using `requests`, the entire response body is downloaded immediately. For large files or streaming APIs, this approach can be inefficient or impractical.

### Normal vs. Streaming Requests

```mermaid
flowchart TD
    subgraph "Normal Request"
        A1["Client"] -->|"GET /resource"| B1["Server"]
        B1 -->|"Response with headers\nand full body"| A1
        A1 -->|"Process entire\nresponse at once"| C1["Complete"]
    end

    subgraph "Streaming Request"
        A2["Client"] -->|"GET /resource\nstream=True"| B2["Server"]
        B2 -->|"Response with\nheaders only"| A2
        A2 -->|"Request chunk 1"| B2
        B2 -->|"Send chunk 1"| A2
        A2 -->|"Process chunk 1"| D2["Process Chunk"]
        A2 -->|"Request chunk 2"| B2
        B2 -->|"Send chunk 2"| A2
        A2 -->|"Process chunk 2"| D2
        D2 -->|"When all chunks\nare processed"| C2["Complete"]
    end
```

Sources: [docs/user/advanced.rst:300-333](), [docs/user/quickstart.rst:170-202]()

When you set `stream=True` in a request, the `requests` library will:

1. Download only the response headers initially [docs/user/quickstart.rst:170-172]().
2. Keep the connection open and use `urllib3` connection pooling for persistence [docs/user/advanced.rst:15-18]().
3. Download the body only when you access `Response.content` or iterate over the response using methods like `iter_content` [docs/user/quickstart.rst:189-193]().

Example:
```python
r = requests.get('https://github.com/psf/requests/tarball/main', stream=True)

# At this point only headers have been downloaded
# You can check headers before deciding to download content
if int(r.headers.get('content-length', 0)) < 10_000_000:  # 10MB
    content = r.content  # This triggers the download
```

## Processing Streaming Responses

The `requests` library provides several methods to work with streaming responses through the `requests.models.Response` class [docs/api.rst:56-59]().

### Response Processing Options

```mermaid
flowchart TD
    A["requests.get(url, stream=True)"] --> B["requests.models.Response"]
    
    B --> C1["Response.iter_content()\nChunk-by-chunk processing"]
    B --> C2["Response.iter_lines()\nLine-by-line processing"]
    B --> C3["Response.raw\nLow-level raw access"]
    
    C1 --> D1["Download file\nin chunks"]
    C1 --> D2["Process binary data\nincrementally"]
    
    C2 --> E1["Process streaming JSON\nor line-based data"]
    C2 --> E2["Read log files\nor event streams"]
    
    C3 --> F1["Direct access to\nurllib3.response.HTTPResponse"]
    C3 --> F2["Custom binary\nprocessing"]
```

Sources: [docs/user/advanced.rst:300-333](), [docs/user/quickstart.rst:183-201](), [docs/api.rst:56-59]()

### 1. Response.iter_content()

The recommended approach for most streaming needs. It iterates over the response data.

```python
with requests.get('https://example.com/large-file', stream=True) as r:
    with open('large-file', 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
```

**Key Features**:
- Automatically handles decoding of `gzip`, `deflate`, and `br` (if brotli is installed) transfer-encodings [docs/user/quickstart.rst:129-132]().
- Allows control over memory usage via `chunk_size`. The default `ITER_CHUNK_SIZE` is 512 [src/requests/models.py:105-105]().
- Works with both binary and text data.

### 2. Response.iter_lines()

Useful for APIs that return line-delimited data (like JSON streaming APIs).

```python
with requests.get('https://httpbin.org/stream/20', stream=True) as r:
    for line in r.iter_lines():
        if line:  # filter out keep-alive new lines
            decoded_line = line.decode('utf-8')
            # Process the line
```

**Important Note**: `iter_lines()` is not reentrant safe. If you need to call it from multiple places, save the iterator [docs/user/advanced.rst:555-565]().

### 3. Response.raw

For low-level access to the raw socket response. This returns a `urllib3.response.HTTPResponse` object [docs/user/quickstart.rst:176-177]().

```python
r = requests.get('https://api.github.com/events', stream=True)
raw_bytes = r.raw.read(10)  # Read 10 bytes
```

**Important Differences**:
- `Response.iter_content()` automatically decodes compression and provides chunks [docs/user/quickstart.rst:196-202]().
- `Response.raw` is a raw stream of bytes with no transformation.
- For most use cases, `iter_content()` is recommended.

## Managing Connections

When using `stream=True`, the connection remains open until all data is consumed or the response is closed. To avoid connection leaks, always use a context manager [docs/user/advanced.rst:324-333]().

```python
with requests.get('https://example.com/large-file', stream=True) as r:
    # Process response here
    pass
# Connection is automatically closed when exiting the with block
```

Sources: [docs/user/advanced.rst:324-333](), [docs/user/advanced.rst:67-73]()

## Chunk-Encoded Requests

HTTP chunked transfer encoding allows sending data without knowing the total size upfront.

### Sending Chunked Requests

To send a chunk-encoded request, provide a generator or iterator as the request body. Requests will automatically set the `Transfer-Encoding: chunked` header [tests/test_lowlevel.py:24-37]().

```python
def gen():
    yield b'hi'
    yield b'there'

requests.post('http://some.url/chunked', data=gen())
```

Sources: [docs/user/advanced.rst:366-380](), [tests/test_lowlevel.py:24-37]()

### Receiving Chunked Responses

For chunk-encoded responses, set `stream=True`. If the server returns a malformed chunked response, `requests` raises a `requests.exceptions.ChunkedEncodingError` [tests/test_lowlevel.py:39-61]().

```python
try:
    r = requests.get('http://some.url/chunked', stream=True)
    for chunk in r.iter_content(chunk_size=None):  # None returns original chunks
        pass
except requests.exceptions.ChunkedEncodingError:
    # Handle bad chunking
    pass
```

Sources: [docs/user/advanced.rst:381-387](), [tests/test_lowlevel.py:39-61](), [docs/api.rst:34-34]()

## Streaming Lifecycle

```mermaid
sequenceDiagram
    participant Client
    participant Session as "requests.sessions.Session"
    participant Adapter as "requests.adapters.HTTPAdapter"
    participant Server
    
    Client->>Session: request(method, url, stream=True)
    Session->>Adapter: send(PreparedRequest, stream=True)
    Adapter->>Server: HTTP Request
    Server->>Adapter: HTTP headers
    Adapter->>Session: urllib3.response.HTTPResponse
    Session->>Client: Return requests.models.Response (body not downloaded)
    
    Note over Client,Server: Connection remains open in urllib3 PoolManager
    
    Client->>Session: Response.iter_content()
    Session->>Server: Fetch next chunk from socket
    Server->>Session: Send chunk data
    Session->>Client: Yield chunk to loop
    
    Note over Client,Server: Repeat until all data received
    
    alt All data consumed
        Client->>Client: Iteration completes
        Client->>Session: Response.close() via context manager
    else Early termination
        Client->>Session: Response.close()
    end
    
    Session->>Adapter: Release connection back to pool
```

Sources: [docs/user/advanced.rst:300-333](), [docs/api.rst:67-72](), [docs/user/advanced.rst:124-150]()

## Implementation Details

### super_len Utility

The utility function `requests.utils.super_len` is used internally to calculate the length of streamable data. It handles various types like files, `BytesIO`, and `StringIO` objects by checking for `__len__`, `len` attributes, or using `tell()` and `seek()` to determine size [tests/test_utils.py:50-155]().

| Type | Calculation Method |
| :--- | :--- |
| String/Bytes | `len()` [tests/test_utils.py:98-99]() |
| File-like | `fstat` via `fileno()` or `tell()`/`seek()` [tests/test_utils.py:139-150]() |
| Objects with `len` | `obj.len` [tests/test_utils.py:132-137]() |

### Data Flow for Iteration

When `Response.iter_content` is called, it wraps the underlying `urllib3` stream. If `decode_unicode` is requested, it uses `requests.utils.stream_decode_response_unicode` to handle character set conversion on the fly [src/requests/models.py:72-83]().

Sources: [src/requests/models.py:72-83](), [tests/test_utils.py:50-155](), [docs/user/quickstart.rst:183-193]()

---

# Page: Proxies and Tunneling

# Proxies and Tunneling

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [docs/api.rst](docs/api.rst)
- [docs/user/advanced.rst](docs/user/advanced.rst)
- [docs/user/quickstart.rst](docs/user/quickstart.rst)
- [src/requests/utils.py](src/requests/utils.py)
- [tests/test_lowlevel.py](tests/test_lowlevel.py)
- [tests/test_testserver.py](tests/test_testserver.py)
- [tests/test_utils.py](tests/test_utils.py)

</details>



This document explains how the Requests library supports HTTP and SOCKS proxies, enabling routing of requests through intermediary servers. It covers configuring proxies for individual requests or sessions, proxy authentication, environment variable configuration, and advanced features like SOCKS proxies and proxy bypassing.

## Overview of Proxy Support

Requests provides robust proxy support, allowing HTTP requests to be routed through intermediary servers. This is useful for network access control, content filtering, anonymity, debugging, and accessing resources in restricted networks.

The following diagram illustrates the relationship between user-facing API calls and the internal utility functions responsible for proxy resolution.

**Proxy Resolution Data Flow**
```mermaid
flowchart TD
    subgraph UserSpace ["User API Space"]
        Session["Session.proxies"]
        ReqParam["proxies parameter"]
    end

    subgraph InternalUtils ["requests.utils (Code Space)"]
        select_proxy["select_proxy(url, proxies)"]
        get_environ_proxies["get_environ_proxies(url)"]
        should_bypass["should_bypass_proxies(url, no_proxy)"]
    end

    subgraph CompatLayer ["requests.compat (Code Space)"]
        getproxies["getproxies()"]
        proxy_bypass["proxy_bypass()"]
    end

    ReqParam --> select_proxy
    Session --> select_proxy
    select_proxy --> should_bypass
    should_bypass --> proxy_bypass
    select_proxy --> get_environ_proxies
    get_environ_proxies --> getproxies
```
Sources: [src/requests/utils.py:441-450](), [src/requests/utils.py:1005-1033](), [src/requests/compat.py:49-54]()

## Configuring Proxies

### For Individual Requests
You can configure proxies for individual requests using the `proxies` parameter. The keys in the dictionary should be the protocol (e.g., `http`, `https`) or a specific host.

```python
import requests

proxies = {
  'http': 'http://10.10.1.10:3128',
  'https': 'http://10.10.1.10:1080',
}

requests.get('http://example.org', proxies=proxies)
```
Sources: [docs/user/advanced.rst:580-591]()

### For Session Objects
For multiple requests, configure proxies at the session level. The `Session` object persists these settings across all requests made within that session.

```python
import requests

s = requests.Session()
s.proxies = {'http': 'http://10.10.1.10:3128'}
s.get('http://example.org')
```
Sources: [docs/user/advanced.rst:592-614]()

## Environment Variables

If no `proxies` argument is passed to a request or session, Requests looks for configuration in standard environment variables via `requests.utils.get_environ_proxies` [src/requests/utils.py:1005-1033]().

| Variable | Purpose |
|----------|---------|
| `http_proxy` | Proxy for HTTP requests |
| `https_proxy` | Proxy for HTTPS requests |
| `no_proxy` | Comma-separated list of hosts/networks to bypass |
| `all_proxy` | Fallback proxy for all protocols |

Sources: [docs/user/advanced.rst:615-629](), [src/requests/utils.py:1005-1020]()

## Proxy Authentication

To use HTTP Basic Authentication with a proxy, use the `http://user:password@host/` syntax within the proxy URL.

```python
proxies = {'http': 'http://user:pass@10.10.1.10:3128/'}
```
Internally, Requests provides `requests.auth.HTTPProxyAuth` to handle these credentials during the connection phase [docs/api.rst:78-78]().

Sources: [docs/user/advanced.rst:630-641](), [docs/api.rst:78-78]()

## Scheme-Specific Proxies

To specify proxies for particular hosts, use the `scheme://hostname` format as the key. This allows fine-grained control over which proxy is used for specific destinations.

```python
proxies = {'http://10.20.1.128': 'http://10.10.1.10:5323'}
```
**Note**: Since Requests 2.x, proxy URLs must include a scheme (e.g., `http://`). Omitting it will raise a `requests.exceptions.MissingSchema` error [docs/api.rst:240-249]().

Sources: [docs/user/advanced.rst:642-651](), [docs/api.rst:240-249]()

## Proxy Selection Process

The logic for selecting which proxy to use for a given URL is encapsulated in `requests.utils.select_proxy`.

**Internal Selection Logic**
```mermaid
flowchart TD
    Start["select_proxy(url, proxies)"] --> CheckBypass["should_bypass_proxies(url)"]
    CheckBypass -- "Yes" --> ReturnNone["Return None (Direct)"]
    CheckBypass -- "No" --> CheckExact["Match url scheme+hostname in proxies dict"]
    
    CheckExact -- "Found" --> ReturnMatch["Return matched proxy"]
    CheckExact -- "Not Found" --> CheckScheme["Match url scheme in proxies dict"]
    
    CheckScheme -- "Found" --> ReturnMatch
    CheckScheme -- "Not Found" --> ReturnNone
```
Sources: [src/requests/utils.py:441-450](), [tests/test_utils.py:495-533]()

## SOCKS Proxy Support

Requests supports SOCKS4 and SOCKS5 protocol proxies. This requires the `PySocks` library, which can be installed via the `socks` extra.

```bash
$ python -m pip install 'requests[socks]'
```

Example usage:
```python
proxies = {
    'http': 'socks5://user:pass@host:port',
    'https': 'socks5h://user:pass@host:port'
}
```
- `socks5`: DNS resolution happens on the client.
- `socks5h`: DNS resolution happens on the proxy server (remote DNS).

Sources: [docs/user/advanced.rst:669-695]()

## Proxy Bypassing and no_proxy

The `no_proxy` setting (via environment variable or argument) allows specific hosts or IP ranges to bypass proxying.

### Matching Logic
Requests implements sophisticated matching in `requests.utils.should_bypass_proxies`. On Windows, if environment variables are not set, it can fall back to the registry via `proxy_bypass_registry` [src/requests/utils.py:99-135]().

The library supports:
- **Hostnames**: `localhost`, `example.com`
- **Domain suffixes**: `.mit.edu` (matches all subdomains)
- **IP Addresses**: `127.0.0.1`
- **CIDR Ranges**: `192.168.0.0/24`

### Implementation Helpers
The library provides several low-level utilities for IP-based bypass logic:
- `is_ipv4_address(host)`: Checks if a string is a valid IPv4 address [src/requests/utils.py:1035-1044]().
- `is_valid_cidr(cidr)`: Validates CIDR notation [src/requests/utils.py:1047-1061]().
- `address_in_network(ip, net)`: Determines if an IP falls within a specific network range [src/requests/utils.py:1064-1080]().
- `dotted_netmask(mask)`: Converts a numerical network mask to dotted-quad notation [src/requests/utils.py:1083-1094]().

Sources: [src/requests/utils.py:96-147](), [src/requests/utils.py:1035-1094](), [tests/test_utils.py:220-254]()

## SSL Certificates with Proxies

When tunneling HTTPS through a proxy, Requests verifies the SSL certificate of the destination server. If the proxy performs SSL inspection (MITM), you must provide the proxy's CA bundle.

1. **Default Bundle**: Requests uses `certifi` via `requests.utils.DEFAULT_CA_BUNDLE_PATH` [src/requests/utils.py:82-82]().
2. **Custom Bundle**: Set `REQUESTS_CA_BUNDLE` or `CURL_CA_BUNDLE` environment variables.

Sources: [src/requests/utils.py:82-82](), [docs/user/advanced.rst:652-668]()

---

# Page: Event Hooks

# Event Hooks

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [docs/api.rst](docs/api.rst)
- [docs/user/advanced.rst](docs/user/advanced.rst)
- [docs/user/quickstart.rst](docs/user/quickstart.rst)
- [src/requests/_internal_utils.py](src/requests/_internal_utils.py)
- [src/requests/exceptions.py](src/requests/exceptions.py)
- [src/requests/hooks.py](src/requests/hooks.py)
- [tests/test_hooks.py](tests/test_hooks.py)

</details>



Event hooks in the Requests library provide a mechanism to intercept and modify the response generated from a request. This feature allows users to inject custom logic into the request-response lifecycle, facilitating tasks like automated logging, data transformation, or custom error handling without modifying the core library code.

## Implementation Details

The hook system is primarily defined in `src/requests/hooks.py` [[src/requests/hooks.py:1-49]](). It utilizes a simple dispatch mechanism where callback functions are stored in a dictionary keyed by the event name.

### Hook Definition and Dispatch
Currently, Requests supports exactly one hook: `response` [[src/requests/hooks.py:7-11]](). The system is designed to handle a list of callable objects for this event [[src/requests/hooks.py:22-26]](). The `default_hooks` function initializes a dictionary with an empty list for the `response` key [[src/requests/hooks.py:25-26]]().

The following diagram illustrates the transition from the high-level API to the internal `dispatch_hook` function.

**Hook Dispatch Flow**
```mermaid
graph TD
    subgraph "Natural Language Space"
        ["User provides callback"] --> ["EventOccurs: Response is received"]
    end

    subgraph "Code Entity Space"
        [HookDict] -- "1. Lookup 'response'" --> [dispatch_hook]
        [dispatch_hook] -- "2. Iterate list" --> [HookType_Callable]
        [HookType_Callable] -- "3. Return modified" --> [dispatch_hook]
        
        subgraph "src/requests/hooks.py"
            [HookDict]
            [dispatch_hook]
        end
    end

    ["User provides callback"] -.-> [HookDict]
    ["EventOccurs: Response is received"] -.-> [dispatch_hook]
```
Sources: [[src/requests/hooks.py:22-48]]()

### Data Flow in dispatch_hook
When `dispatch_hook` is called, it iterates through the registered functions for a given key. If a hook returns a value, that value replaces the current data being processed, which is then passed to the next hook in the chain [[src/requests/hooks.py:32-48]]().

| Component | Role | Source |
|:---|:---|:---|
| `HOOKS` | Constant list containing `['response']` | [[src/requests/hooks.py:22]]() |
| `default_hooks()` | Returns a dict with empty lists for all available hooks | [[src/requests/hooks.py:25-26]]() |
| `dispatch_hook()` | The execution engine that iterates and applies callbacks | [[src/requests/hooks.py:32-48]]() |
| `HookType` | Type alias for the callable signature (from `_types`) | [[src/requests/hooks.py:19]]() |

Sources: [[src/requests/hooks.py:1-49]]()

## Using Hooks

Hooks can be applied at two levels: per-request or at the session level.

### Per-request Hooks
Users can pass a `hooks` dictionary to any request method (e.g., `get()`, `post()`). The dictionary should map `'response'` to a callable or a list of callables [[docs/user/quickstart.rst:32-48]](). If a single callable is provided, `dispatch_hook` wraps it in a list before execution [[src/requests/hooks.py:42-43]]().

```python
def print_url(r, *args, **kwargs):
    print(r.url)

requests.get('https://httpbin.org/', hooks={'response': print_url})
```

### Session-level Hooks
Hooks registered on a `Session` object are persisted across all requests made with that session [[docs/user/advanced.rst:13-18]](). This is achieved by initializing the session with `default_hooks()` [[src/requests/hooks.py:25-26]]().

```python
s = requests.Session()
s.hooks['response'].append(print_url)
```

**Hook Lifecycle Diagram**
```mermaid
sequenceDiagram
    participant U as "User Code"
    participant S as "Session/Request"
    participant H as "dispatch_hook()"
    participant C as "Callback Function"

    U->>S: "request(hooks={'response': func})"
    S->>S: "Perform HTTP Transaction"
    S->>H: "dispatch_hook('response', hooks, response)"
    loop "for each hook in hook_list"
        H->>C: "hook(response, **kwargs)"
        alt "returns value"
            C-->>H: "modified_response"
        else "returns None"
            C-->>H: "continue with original"
        end
    end
    H-->>S: "final_response"
    S-->>U: "Response Object"
```
Sources: [[src/requests/hooks.py:32-48]](), [[tests/test_hooks.py:6-19]]()

## Technical Constraints and Behavior

1.  **Modification In-Place**: If a hook function returns `None`, the original response object is retained. If it returns a value, that value replaces the response for subsequent hooks and the final return [[src/requests/hooks.py:45-47]]().
2.  **Argument Passing**: Hooks receive the response object as the first argument. Additional keyword arguments passed to `dispatch_hook` (like `timeout` or `stream`) are forwarded to the hook via `**kwargs` [[src/requests/hooks.py:45]]().
3.  **Order of Execution**: Hooks are executed in the order they appear in the list [[src/requests/hooks.py:44]]().
4.  **Error Handling**: The hook system does not provide internal try-except blocks; exceptions raised within a hook will propagate up the call stack to the user [[src/requests/hooks.py:45]]().
5.  **Return Value Requirements**: For a hook to effectively modify the chain, it must return the modified object; otherwise, the original object persists [[src/requests/hooks.py:46-47]]().

## Comparison with Authentication Hooks
While `AuthBase` implementations also intercept the request flow, they operate on the `PreparedRequest` object *before* the request is sent [[docs/api.rst:76-79]](). Event hooks, specifically the `response` hook, operate on the `Response` object *after* the request has been completed [[src/requests/hooks.py:9-11]]().

**Post-Request vs Pre-Request Logic**
```mermaid
graph LR
    subgraph "Pre-Request Phase"
        [AuthBase_call] -- "Modifies" --> [PreparedRequest]
    end
    
    [PreparedRequest] -- "Adapter.send" --> [Network]
    [Network] -- "Returns" --> [Response]
    
    subgraph "Post-Request Phase"
        [dispatch_hook] -- "Modifies" --> [Response]
    end

    subgraph "src/requests/auth.py"
        [AuthBase_call]
    end

    subgraph "src/requests/hooks.py"
        [dispatch_hook]
    end
```
Sources: [[src/requests/hooks.py:32-48]](), [[docs/api.rst:76-79]]()

| Feature | Event Hooks (`response`) | Authentication (`AuthBase`) |
|:---|:---|:---|
| **Target Object** | `Response` | `PreparedRequest` |
| **Timing** | Post-Request | Pre-Request |
| **Location** | `src/requests/hooks.py` | `src/requests/auth.py` |
| **Interface** | Function/Callable | `__call__` method in class |

Sources: [[src/requests/hooks.py:32-48]](), [[docs/api.rst:76-79]]()

---

# Page: Timeout Configuration

# Timeout Configuration

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [AUTHORS.rst](AUTHORS.rst)
- [docs/api.rst](docs/api.rst)
- [docs/user/advanced.rst](docs/user/advanced.rst)
- [docs/user/quickstart.rst](docs/user/quickstart.rst)
- [src/requests/adapters.py](src/requests/adapters.py)
- [tests/test_adapters.py](tests/test_adapters.py)
- [tests/test_requests.py](tests/test_requests.py)

</details>



## Purpose and Scope

This document provides a detailed explanation of timeout configuration in the Requests library. It covers the two types of timeouts (connect and read), configuration methods, timing behavior, and implementation details within the transport layer.

For information about SSL certificate verification settings, see [SSL Verification](#4.1). For proxy configuration, see [Proxies and Tunneling](#4.3). For general session-level configuration, see [Session Management](#2.2).

---

## Overview

Timeouts are a critical safety mechanism that prevent requests from hanging indefinitely when servers are unresponsive or network issues occur. By default, Requests does **not** impose any timeout, meaning a request can block forever if the server never responds. This behavior is acceptable for interactive scripts but unsuitable for production systems.

**Key principle**: Nearly all production code should specify a `timeout` parameter in nearly all requests to prevent indefinite blocking.

Sources: `[docs/user/advanced.rst:438-441]()`, `[docs/user/quickstart.rst:532-535]()`

---

## Timeout Types

Requests supports two distinct timeout values that control different phases of the HTTP request lifecycle:

### Connect Timeout

The **connect timeout** is the maximum number of seconds Requests will wait for the client to establish a TCP connection to the remote server. This corresponds to the underlying socket `connect()` system call.

**Recommended practice**: Set connect timeouts to slightly larger than a multiple of 3 seconds, which is the default TCP packet retransmission window defined in RFC 2988. This allows for natural retry behavior at the TCP level.

Example values: `3.05`, `6.1`, `9.15` seconds.

Sources: `[docs/user/advanced.rst:443-447]()`

### Read Timeout

The **read timeout** is the maximum number of seconds the client will wait for the server to send data after the connection is established and the HTTP request has been sent. Specifically, it measures the time between bytes received from the server. In most cases, this represents the time before the server sends the first byte of the response.

**Important**: The read timeout is **not** a time limit on the entire response download. It only triggers if the server stops sending data for the specified duration.

Sources: `[docs/user/advanced.rst:449-453]()`, `[docs/user/quickstart.rst:545-549]()`

---

## Configuration Methods

### Single Value Timeout

When a single numeric value is provided, it applies to **both** connect and read timeouts:

```python
import requests

# Both connect and read timeout set to 5 seconds
r = requests.get('https://github.com', timeout=5)
```

Sources: `[docs/user/advanced.rst:455-457]()`

### Tuple Timeout (Separate Connect and Read)

To configure connect and read timeouts independently, pass a tuple of `(connect_timeout, read_timeout)`:

```python
# Connect timeout: 3.05 seconds
# Read timeout: 27 seconds
r = requests.get('https://github.com', timeout=(3.05, 27))
```

This is useful when you expect the server to be responsive in establishing connections but may take longer to generate responses (e.g., long-running queries).

Sources: `[docs/user/advanced.rst:459-462]()`

### No Timeout (None)

Passing `None` as the timeout value disables timeouts entirely, allowing the request to wait indefinitely:

```python
# Wait forever for a response
r = requests.get('https://github.com', timeout=None)
```

This is the default behavior when no timeout is specified, but using `timeout=None` explicitly documents the intent.

Sources: `[docs/user/advanced.rst:464-470]()`

---

## Implementation and Data Flow

The `timeout` parameter is passed from the top-level API down to the `HTTPAdapter`, where it is converted into a `urllib3.util.Timeout` object (aliased as `TimeoutSauce` in the adapter).

### Data Flow: API to Transport

```mermaid
sequenceDiagram
    participant User
    participant API as "requests.api.request()"
    participant Session as "requests.sessions.Session"
    participant Adapter as "requests.adapters.HTTPAdapter"
    participant PM as "urllib3.poolmanager.PoolManager"
    participant Socket as "TCP Socket"

    User->>API: "get(url, timeout=(3.05, 27))"
    API->>Session: "request(method, url, timeout=(3.05, 27))"
    Session->>Adapter: "send(request, timeout=(3.05, 27))"
    
    Note over Adapter: "Convert to urllib3.util.TimeoutSauce"
    Adapter->>PM: "urlopen(timeout=TimeoutSauce(connect=3.05, read=27))"
    
    Note over PM,Socket: "Connect Phase"
    PM->>Socket: "connect() with 3.05s timeout"
    
    alt Connection succeeds
        Socket-->>PM: "Connected"
        Note over PM,Socket: "Read Phase"
        PM->>Socket: "recv() with 27s read timeout"
        Socket-->>Adapter: "Response bytes"
        Adapter-->>User: "Response object"
    else Connect timeout
        Socket-->>PM: "ConnectTimeoutError"
        PM-->>Adapter: "ConnectTimeoutError"
        Adapter-->>User: "raises ConnectTimeout"
    end
```

**Diagram: Timeout Parameter Flow**

This diagram shows how the `timeout` parameter flows through the system. The `HTTPAdapter.send` method receives the `timeout` `[src/requests/adapters.py:132-136]()` and passes it to `urllib3`'s `PoolManager.urlopen` via the transport layer `[src/requests/adapters.py:440-442]()` (implied in full source). The adapter uses `TimeoutSauce` (urllib3's Timeout utility) to structure these constraints `[src/requests/adapters.py:32]()`.

Sources: `[src/requests/adapters.py:32]()`, `[src/requests/adapters.py:132-136]()`, `[docs/user/advanced.rst:143-149]()`

---

## Timeout Behavior and Edge Cases

### Multiple IP Addresses

When a domain name resolves to multiple IP addresses, the underlying `urllib3` library attempts to connect to each address sequentially. The connect timeout applies to **each individual connection attempt**, not the total time across all attempts.

**Consequence**: If a server has both IPv4 and IPv6 addresses and both are unresponsive, the effective total connection timeout can be **double** the specified timeout.

Sources: `[docs/user/advanced.rst:472-478]()`

### Wall Clock Time vs Timeout Value

Neither connect nor read timeouts represent total wall clock time for the request. The actual elapsed time may exceed the specified timeout value due to:

- Multiple connection attempts for multi-IP hosts.
- Internal retry logic in `urllib3` (configured via `max_retries` in `HTTPAdapter`).
- Operating system delays.

Sources: `[docs/user/advanced.rst:479-482]()`, `[src/requests/adapters.py:168-174]()`

---

## Timeout Exception Hierarchy

Timeout-related exceptions inherit from `requests.exceptions.Timeout`, which itself inherits from `requests.exceptions.RequestException`.

### Exception Mapping

```mermaid
graph TD
    RE["requests.exceptions.RequestException"]
    T["requests.exceptions.Timeout"]
    CT["requests.exceptions.ConnectTimeout"]
    RT["requests.exceptions.ReadTimeout"]
    
    RE --> T
    T --> CT
    T --> RT

    subgraph "urllib3_Mapping"
        UCT["urllib3.exceptions.ConnectTimeoutError"]
        URT["urllib3.exceptions.ReadTimeoutError"]
    end

    UCT -.->|mapped_to| CT
    URT -.->|mapped_to| RT
```

**Diagram: Timeout Exception Hierarchy and Mapping**

| Exception | Description | Source |
|-----------|-------------|--------|
| `ConnectTimeout` | Raised when the connection to the server times out. | `[src/requests/adapters.py:41]()`, `[tests/test_requests.py:36]()` |
| `ReadTimeout` | Raised when the server does not send data within the read timeout period. | `[src/requests/adapters.py:47]()`, `[tests/test_requests.py:44]()` |
| `Timeout` | Base class for both `ConnectTimeout` and `ReadTimeout`. | `[tests/test_requests.py:47]()` |

Sources: `[tests/test_requests.py:33-50]()`, `[src/requests/adapters.py:39-50]()`, `[src/requests/adapters.py:19-24]()`

---

## Advanced Usage

### Streaming Responses

When using `stream=True`, the read timeout applies to reading each chunk of data from the response, not the total download time. This is handled by `Response.iter_content` `[docs/user/quickstart.rst:189-194]()`.

```python
# Read timeout applies to each iteration of content
r = requests.get('https://example.com/large-file', stream=True, timeout=(3.05, 5))

for chunk in r.iter_content(chunk_size=1024):
    process(chunk)
```

Sources: `[docs/user/quickstart.rst:172-181]()`, `[docs/user/advanced.rst:306-332]()`, `[docs/user/quickstart.rst:189-194]()`

### Retries and Timeouts

The `HTTPAdapter` allows configuring `max_retries`. If a connection attempt fails due to a `ConnectTimeout`, the adapter may retry the request if configured to do so. The timeout value applies to **each** retry attempt. By default, `HTTPAdapter` uses `DEFAULT_RETRIES` which is 0 `[src/requests/adapters.py:81]()`.

```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

s = requests.Session()
retries = Retry(total=3, read=False)
s.mount('https://', HTTPAdapter(max_retries=retries))

# Each attempt has a 5s timeout
s.get('https://api.example.com', timeout=5)
```

Sources: `[src/requests/adapters.py:81]()`, `[src/requests/adapters.py:168-174]()`, `[src/requests/adapters.py:208-211]()`

---

## Best Practices

1.  **Always set a timeout**: Avoid using the default (infinite) timeout in production code `[docs/user/advanced.rst:438-441]()`.
2.  **Use Tuple Timeouts**: For critical infrastructure, use `(connect, read)` tuples to allow longer for response generation while failing fast on connection issues `[docs/user/advanced.rst:459-462]()`.
3.  **Conservative Connect Timeouts**: Use values slightly above 3 seconds (e.g., `3.05`) to account for TCP retransmission windows `[docs/user/advanced.rst:443-447]()`.
4.  **Handle Exceptions**: Always wrap requests in `try/except` blocks for `requests.exceptions.Timeout` `[tests/test_requests.py:111-114]()`.

Sources: `[docs/user/advanced.rst:438-482]()`, `[docs/user/quickstart.rst:532-569]()`

---

# Page: Utility Functions

# Utility Functions

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [src/requests/utils.py](src/requests/utils.py)
- [tests/test_lowlevel.py](tests/test_lowlevel.py)
- [tests/test_testserver.py](tests/test_testserver.py)
- [tests/test_utils.py](tests/test_utils.py)

</details>



The Requests library provides a comprehensive set of utility functions that support the core request/response functionality. These utility functions handle common HTTP and networking tasks such as URL manipulation, header parsing, content encoding detection, and proxy configuration. They serve as the foundation for many of the higher-level features in Requests, making the library both powerful and user-friendly.

This page documents the key utility functions available in the Requests library, their purpose, and usage patterns.

## Overview of Utility Functions

Utility functions in Requests can be broadly categorized into several groups based on their purpose:

```mermaid
graph TD
    subgraph "Utility Function Categories"
        URL["URL Management<br>- requote_uri<br>- unquote_unreserved<br>- prepend_scheme_if_needed"]
        Headers["Header Processing<br>- parse_dict_header<br>- _parse_list_header<br>- get_encoding_from_headers"]
        Content["Content Handling<br>- super_len<br>- iter_slices<br>- guess_json_utf"]
        Network["Network & Proxy<br>- get_environ_proxies<br>- should_bypass_proxies<br>- address_in_network"]
        Cookie["Cookie Management<br>- add_dict_to_cookiejar<br>- cookiejar_from_dict"]
        File["File Operations<br>- guess_filename<br>- extract_zipped_paths"]
    end

    "Session[requests.sessions.Session]" --> URL
    "Session[requests.sessions.Session]" --> Headers
    "Session[requests.sessions.Session]" --> Content
    "Session[requests.sessions.Session]" --> Network
    "Session[requests.sessions.Session]" --> Cookie
    
    "HTTPAdapter[requests.adapters.HTTPAdapter]" --> URL
    "HTTPAdapter[requests.adapters.HTTPAdapter]" --> Headers
    "HTTPAdapter[requests.adapters.HTTPAdapter]" --> Content
    "HTTPAdapter[requests.adapters.HTTPAdapter]" --> Network
```

Sources: [src/requests/utils.py:1-7]()

## URL Handling Utilities

The URL handling utilities help manage and manipulate URLs throughout the request lifecycle, ensuring that characters are correctly escaped and schemes are present.

```mermaid
flowchart TD
    subgraph "URL Utility Functions"
        direction LR
        rawURL["Raw URL"] --> "requote_uri[requests.utils.requote_uri]"
        "requote_uri[requests.utils.requote_uri]" --> sanitizedURL["Sanitized URL"]
        
        urlWithAuth["URL with Auth"] --> "get_auth_from_url[requests.utils.get_auth_from_url]"
        "get_auth_from_url[requests.utils.get_auth_from_url]" --> authCredentials["Auth Credentials"]
        
        schemeURL["URL without Scheme"] --> "prepend_scheme_if_needed[requests.utils.prepend_scheme_if_needed]"
        "prepend_scheme_if_needed[requests.utils.prepend_scheme_if_needed]" --> completeURL["Complete URL"]
        
        urlWithFragment["URL with Fragment"] --> "urldefragauth[requests.utils.urldefragauth]"
        "urldefragauth[requests.utils.urldefragauth]" --> cleanURL["Clean URL"]
    end
```

### Key URL Utility Functions

- **`requote_uri(uri)`**: Safely re-quotes a URI, ensuring it's properly encoded while preserving already encoded characters [src/requests/utils.py:643-665]().
- **`unquote_unreserved(uri)`**: Un-escapes any percent-escape sequences in a URI that are unreserved characters [src/requests/utils.py:668-683]().
- **`get_auth_from_url(url)`**: Extracts the user and password from a URL for HTTP Basic Authentication [src/requests/utils.py:873-888]().
- **`urldefragauth(url)`**: Removes authentication and fragment components from a URL [src/requests/utils.py:904-918]().
- **`prepend_scheme_if_needed(url, scheme)`**: Adds a scheme (e.g., "http") to a URL if it doesn't already have one [src/requests/utils.py:921-930]().

Sources: [src/requests/utils.py:643-930](), [tests/test_utils.py:416-480]()

## Header Processing Utilities

The header processing utilities help parse, validate, and extract information from HTTP headers.

### Header Parsing Functions

- **`parse_dict_header(value)`**: Parses a HTTP header value as a dictionary (e.g., for `Digest` auth or `Content-Disposition`) [src/requests/utils.py:392-411]().
- **`_parse_list_header(value)`**: Internal alias for `parse_http_list`, used to parse comma-separated headers [src/requests/utils.py:61-61]().
- **`unquote_header_value(value, is_filename=False)`**: Unquotes a header value, handling escaped characters [src/requests/utils.py:346-374]().
- **`parse_header_links(value)`**: Parses the HTTP `Link` header into a list of dictionaries [src/requests/utils.py:414-442]().

Sources: [src/requests/utils.py:346-442](), [tests/test_utils.py:543-666]()

## Content Handling Utilities

Content handling utilities help with determining content length and processing payload data.

### Length Determination with `super_len`

The `super_len` function determines the length of various objects (strings, files, IO streams), supporting multiple ways of calculating length even when the object has been partially read.

```mermaid
flowchart TD
    subgraph "super_len() Logic"
        input["Input Object"] --> checkMethod["Check Methods"]
        checkMethod -->|"__len__"| useLen["len(o)"]
        checkMethod -->|"o.len"| useAttr["o.len"]
        checkMethod -->|"fileno"| useFstat["os.fstat(fileno)"]
        checkMethod -->|"tell/seek"| useSeek["seek(0,2) then tell()"]
        
        useLen --> returnLength["Return Length"]
        useAttr --> returnLength
        useFstat --> returnLength
        useSeek --> returnLength
    end
```

Sources: [src/requests/utils.py:160-251](), [tests/test_utils.py:50-153]()

### Content Detection
Requests provides utilities to detect encoding from headers and HTML content. For a deep dive into how Requests handles character sets, see **[Content Encoding Detection](#5.3)**.

- **`get_encoding_from_headers(headers)`**: Returns the encoding specified in the `Content-Type` header [src/requests/utils.py:517-531]().
- **`get_encodings_from_content(content)`**: Extracts encodings from HTML `<meta>` tags [src/requests/utils.py:534-550]().
- **`guess_json_utf(data)`**: Detects the specific UTF encoding of JSON data by examining byte patterns [src/requests/utils.py:569-601]().

Sources: [src/requests/utils.py:517-601]()

## Network and Proxy Utilities

Requests includes sophisticated logic for resolving proxies and checking IP network membership. For detailed information on proxy selection logic, see **[Proxy Resolution](#5.2)**.

### Proxy and IP Functions

- **`get_environ_proxies(url, no_proxy=None)`**: Returns a dictionary of proxies defined in environment variables like `HTTP_PROXY` or `HTTPS_PROXY` [src/requests/utils.py:769-790]().
- **`select_proxy(url, proxies)`**: Selects the appropriate proxy URL for a given target URL from a dictionary of proxies [src/requests/utils.py:793-803]().
- **`should_bypass_proxies(url, no_proxy=None)`**: Determines if proxies should be bypassed based on the `NO_PROXY` environment variable or Windows registry settings [src/requests/utils.py:806-864]().
- **`address_in_network(ip, net)`**: Checks if an IP address belongs to a CIDR network [src/requests/utils.py:726-743]().

Sources: [src/requests/utils.py:726-864](), [tests/test_utils.py:220-231]()

## Data Structures and Conversions

Requests uses several specialized data structures to handle HTTP-specific behaviors. For details, see **[Custom Data Structures](#5.1)**.

- **`CaseInsensitiveDict`**: A dictionary that allows case-insensitive key access, used primarily for HTTP headers [src/requests/structures.py:13-104]().
- **`to_key_val_list(value)`**: Converts various input formats (dicts, lists of tuples) into a standardized list of key-value pairs [src/requests/utils.py:254-261]().
- **`dict_to_sequence(d)`**: Converts a dictionary-like object to a sequence of items [src/requests/utils.py:149-157]().

Sources: [src/requests/utils.py:149-261](), [src/requests/structures.py:13-104]()

## File Handling Utilities

- **`guess_filename(obj)`**: Tries to guess the filename of a file-like object by checking the `name` attribute [src/requests/utils.py:264-278]().
- **`extract_zipped_paths(path)`**: Handles paths that point to members inside a ZIP archive by extracting them to temporary files [src/requests/utils.py:281-318]().

Sources: [src/requests/utils.py:264-318](), [tests/test_utils.py:291-341]()

---

# Page: Custom Data Structures

# Custom Data Structures

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [src/requests/status_codes.py](src/requests/status_codes.py)
- [src/requests/structures.py](src/requests/structures.py)
- [tests/test_structures.py](tests/test_structures.py)

</details>



This page documents the specialized data structures implemented in the Requests library. These structures provide specific functionality for handling HTTP headers, status codes, and other protocol-specific requirements that standard Python data structures do not fully address.

## Overview

The Requests library implements two primary custom data structures in the `requests.structures` module:

1. `CaseInsensitiveDict`: A `MutableMapping` variant that provides case-insensitive access to keys while preserving the original case for display and iteration [src/requests/structures.py:20-45]().
2. `LookupDict`: A dictionary subclass that allows attribute-style access and provides a default `None` value for missing keys [src/requests/structures.py:96-130]().

Sources: [src/requests/structures.py:1-7](), [tests/test_structures.py:3]()

## CaseInsensitiveDict

`CaseInsensitiveDict` is a dictionary-like object that implements the `MutableMapping` interface. It is primarily used for HTTP headers, which are case-insensitive according to RFCs [src/requests/structures.py:20-45]().

### Implementation Details

The class maintains an internal `OrderedDict` named `_store` [src/requests/structures.py:47](). 

- **Storage**: When a value is set via `__setitem__`, the key is lowercased and used as the internal key. The value is stored as a tuple containing `(original_key, value)` [src/requests/structures.py:59-62]().
- **Retrieval**: Lookups in `__getitem__` convert the provided key to lowercase before accessing `_store` [src/requests/structures.py:64-65]().
- **Iteration**: When iterating over the dictionary (`__iter__`), it yields the `original_key` from the stored tuple, preserving the case of the last key set [src/requests/structures.py:70-71]().
- **Equality**: Equality comparison (`__eq__`) is case-insensitive. It constructs a temporary `CaseInsensitiveDict` from the comparison object and compares their `lower_items()` [src/requests/structures.py:80-86]().

### Technical Specification

| Method | Signature | Description |
|--------|-----------|-------------|
| `__setitem__` | `(key: str, value: _VT)` | Lowercases `key` for `_store` and saves `(key, value)` [src/requests/structures.py:59-62](). |
| `lower_items` | `() -> Iterator[tuple[str, _VT]]` | Yields `(lowercase_key, value)` pairs [src/requests/structures.py:76-78](). |
| `copy` | `() -> CaseInsensitiveDict` | Returns a new instance populated with the same values [src/requests/structures.py:89-90](). |

### Data Flow: Key-Value Lifecycle

The following diagram illustrates how "Natural Language" keys (like "Accept") are transformed into "Code Entities" within the `_store`.

Title: Key Storage and Retrieval Flow
```mermaid
graph LR
    User["User Code"] -- "cid['Accept'] = 'app/json'" --> SetItem["__setitem__"]
    subgraph "CaseInsensitiveDict_Entity"
        SetItem --> Store["_store: OrderedDict"]
        Store -- "key: 'accept'" --> Entry["tuple: ('Accept', 'app/json')"]
    end
    User -- "cid['ACCEPT']" --> GetItem["__getitem__"]
    GetItem -- "lower('ACCEPT')" --> Store
    Store -- "returns value[1]" --> User
```

Sources: [src/requests/structures.py:59-71](), [tests/test_structures.py:6-51]()

## LookupDict

`LookupDict` is a specialized dictionary designed for status code lookups. It allows developers to access status codes as attributes (e.g., `codes.ok`) or as dictionary keys (e.g., `codes['ok']`) [src/requests/structures.py:96-130]().

### Implementation Details

- **Attribute Access**: It overrides `__getattr__` to look up keys in the internal `__dict__`. If the key is missing, it raises an `AttributeError` [src/requests/structures.py:108-116]().
- **Item Access**: It overrides `__getitem__` to return `None` instead of raising a `KeyError` if a key is missing from `__dict__` [src/requests/structures.py:118-121]().
- **Naming**: It includes a `name` attribute primarily used for its string representation in `__repr__` [src/requests/structures.py:101-106]().

### Comparison with Standard Dict

| Feature | Standard `dict` | `LookupDict` |
|---------|-----------------|--------------|
| Missing Key | Raises `KeyError` | Returns `None` [src/requests/structures.py:121]() |
| Attribute Access | No | Yes [src/requests/structures.py:108]() |
| `repr` | `{...}` | `<lookup 'name'>` [src/requests/structures.py:105-106]() |

### Code Entity Association: Status Codes

This diagram shows how the `LookupDict` bridges the gap between human-readable status names and integer codes, specifically as used in `requests.status_codes`.

Title: Status Code Mapping Logic
```mermaid
graph TD
    subgraph "requests_status_codes_codes_LookupDict"
        LC["codes: LookupDict"]
        LC -- "bad_gateway" --> V502["502"]
        LC -- "not_found" --> V404["404"]
        LC -- "ok" --> V200["200"]
    end
    
    User["Developer Code"] -- "codes.bad_gateway" --> LC
    User -- "codes['not_found']" --> LC
    User -- "codes['unknown']" --> NoneResult["None (Graceful Fallback)"]
```

Sources: [src/requests/structures.py:118-121](), [src/requests/status_codes.py:106-115](), [tests/test_structures.py:54-91]()

## Class Hierarchy

The custom structures inherit from Python's collection types to ensure compatibility with standard library functions and type checkers.

Title: Structures Inheritance Hierarchy
```mermaid
classDiagram
    class Mapping {
        <<interface>>
    }
    class MutableMapping {
        <<interface>>
    }
    class dict {
    }
    class CaseInsensitiveDict {
        -_store: OrderedDict
        +lower_items()
        +copy()
    }
    class LookupDict {
        +name: Any
        +get(key, default)
    }

    Mapping <|-- MutableMapping
    MutableMapping <|-- CaseInsensitiveDict
    dict <|-- LookupDict
```

Sources: [src/requests/structures.py:20](), [src/requests/structures.py:96](), [src/requests/compat.py:14]()

## Usage in Requests Components

These data structures are foundational to the library's models:

- **Headers**: Both `PreparedRequest.headers` and `Response.headers` use `CaseInsensitiveDict` to ensure that `r.headers['content-type']` works even if the server sends `Content-Type` [src/requests/structures.py:38-40]().
- **Status Codes**: The `requests.codes` object is an instance of `LookupDict` [src/requests/status_codes.py:106](). It is initialized in `requests.status_codes._init` by mapping various titles (e.g., "ok", "OK", "okay") from the `_codes` dictionary to their integer status codes using `setattr` [src/requests/status_codes.py:109-115]().

Sources: [src/requests/structures.py:1-6](), [src/requests/status_codes.py:23-128](), [tests/test_structures.py:1-91]()

---

# Page: Proxy Resolution

# Proxy Resolution

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [src/requests/utils.py](src/requests/utils.py)
- [tests/test_lowlevel.py](tests/test_lowlevel.py)
- [tests/test_testserver.py](tests/test_testserver.py)
- [tests/test_utils.py](tests/test_utils.py)

</details>



## Purpose and Scope

This document details the proxy resolution system in the Requests library, which determines whether and which proxy server should be used for a given HTTP request. The system handles multiple configuration sources, implements sophisticated bypass rules including CIDR notation for IP ranges, and integrates environment variables with explicit proxy settings.

For information about configuring proxies at the user level, see [4.3](). For details on SSL certificate verification with proxies, see [4.1]().

## Overview

The proxy resolution system evaluates each HTTP request to determine if a proxy should be used and which proxy is appropriate. The system considers:

1. **Explicit proxy configuration**: Proxies specified in code via the `proxies` parameter.
2. **Environment variables**: Standard proxy environment variables (`http_proxy`, `https_proxy`, `no_proxy`, etc.).
3. **Bypass rules**: The `no_proxy` configuration that specifies when proxies should be skipped.
4. **Platform-specific behavior**: Windows registry settings on Windows systems.
5. **URL scheme and hostname matching**: Different proxies for different protocols and hosts.

Sources: [src/requests/utils.py:852-876](), [src/requests/utils.py:753-811]()

## Proxy Resolution Flow

```mermaid
flowchart TD
    Start["Request with URL"] --> ResolveProxies["resolve_proxies()"]
    ResolveProxies --> CheckTrustEnv{"trust_env == True?"}
    
    CheckTrustEnv -->|No| UseExplicit["Use explicit proxies only"]
    CheckTrustEnv -->|Yes| ShouldBypass["should_bypass_proxies(url, no_proxy)"]
    
    ShouldBypass --> CheckNoProxy{"no_proxy defined?"}
    CheckNoProxy -->|Yes| EvaluateNoProxy["Evaluate no_proxy rules"]
    CheckNoProxy -->|No| CheckProxyBypass["Check platform proxy_bypass()"]
    
    EvaluateNoProxy --> IsIPv4{"Is hostname IPv4?"}
    IsIPv4 -->|Yes| CheckCIDR["Check CIDR ranges"]
    IsIPv4 -->|No| CheckHostMatch["Check hostname/port matching"]
    
    CheckCIDR --> BypassDecision{"Match found?"}
    CheckHostMatch --> BypassDecision
    CheckProxyBypass --> BypassDecision
    
    BypassDecision -->|Yes| NoProxy["Return empty proxy dict"]
    BypassDecision -->|No| GetEnvProxies["get_environ_proxies()"]
    
    GetEnvProxies --> SelectProxy["select_proxy(url, proxies)"]
    UseExplicit --> SelectProxy
    
    SelectProxy --> CheckSchemeHost{"Check scheme://host key"}
    CheckSchemeHost -->|Match| UseMatchedProxy["Use matched proxy"]
    CheckSchemeHost -->|No match| CheckScheme{"Check scheme key"}
    CheckScheme -->|Match| UseSchemeProxy["Use scheme proxy"]
    CheckScheme -->|No match| CheckAll{"Check 'all' key"}
    CheckAll -->|Match| UseAllProxy["Use 'all' proxy"]
    CheckAll -->|No match| NoProxyFound["Return None"]
    
    UseMatchedProxy --> End["Proxy URL or None"]
    UseSchemeProxy --> End
    UseAllProxy --> End
    NoProxyFound --> End
    NoProxy --> End
```

**Diagram: Complete Proxy Resolution Flow**

This diagram shows the complete decision tree from request initiation to final proxy selection, including the bypass evaluation and proxy selection steps.

Sources: [src/requests/utils.py:852-876](), [src/requests/utils.py:753-823](), [src/requests/utils.py:826-849]()

## Configuration Sources

### Environment Variables

The system reads standard proxy-related environment variables. The `get_environ_proxies` function utilizes `getproxies()` from `requests.compat` (which wraps `urllib.request.getproxies`).

| Environment Variable | Purpose | Example |
|---------------------|---------|---------|
| `http_proxy` / `HTTP_PROXY` | HTTP proxy URL | `http://10.10.1.10:3128` |
| `https_proxy` / `HTTPS_PROXY` | HTTPS proxy URL | `http://10.10.1.10:1080` |
| `all_proxy` / `ALL_PROXY` | Fallback proxy for all schemes | `socks5://10.10.1.10:3434` |
| `no_proxy` / `NO_PROXY` | Comma-separated bypass list | `192.168.0.0/24,localhost` |

The lowercase variants take precedence over uppercase in many environments to maintain consistency with tools like curl.

Sources: [src/requests/utils.py:814-823](), [src/requests/compat.py:46-60]()

### Explicit Proxies Dictionary

Proxies can be specified programmatically via the `proxies` parameter with keys supporting multiple formats:

```python
proxies = {
    'http': 'http://10.10.1.10:3128',           # Scheme-level
    'https': 'http://10.10.1.10:1080',          # Scheme-level
    'http://example.com': 'http://proxy.local', # Scheme+host specific
    'all': 'socks5://proxy.local',              # Fallback for all
}
```

Sources: [src/requests/utils.py:826-849]()

## Proxy Bypass Mechanism

### The should_bypass_proxies Function

The core proxy bypass logic is implemented in `should_bypass_proxies(url, no_proxy)` at [src/requests/utils.py:753-811](). This function returns `True` if the proxy should be skipped for the given URL.

```mermaid
flowchart TD
    Input["should_bypass_proxies(url, no_proxy)"] --> ParseURL["urlparse(url)"]
    ParseURL --> CheckHostname{"parsed.hostname is None?"}
    CheckHostname -->|Yes| ReturnTrue["Return True (file:// URLs)"]
    
    CheckHostname -->|No| GetNoProxy["Get no_proxy from env if not provided"]
    GetNoProxy --> CheckNoProxyExists{"no_proxy defined?"}
    
    CheckNoProxyExists -->|No| CallProxyBypass["Call platform proxy_bypass()"]
    CheckNoProxyExists -->|Yes| SplitNoProxy["Split no_proxy by comma"]
    
    SplitNoProxy --> CheckIPv4{"is_ipv4_address(hostname)?"}
    
    CheckIPv4 -->|Yes| IPv4Loop["For each entry in no_proxy"]
    IPv4Loop --> IsCIDR{"is_valid_cidr(entry)?"}
    IsCIDR -->|Yes| AddressInNetwork["address_in_network(hostname, entry)"]
    IsCIDR -->|No| ExactIPMatch{"hostname == entry?"}
    
    AddressInNetwork -->|True| ReturnTrueBypass["Return True"]
    ExactIPMatch -->|True| ReturnTrueBypass
    
    CheckIPv4 -->|No| HostnameLoop["For each host in no_proxy"]
    HostnameLoop --> BuildHostPort["Build host_with_port if port present"]
    BuildHostPort --> CheckEndsWith{"hostname.endswith(host) OR host_with_port.endswith(host)?"}
    
    CheckEndsWith -->|True| ReturnTrueBypass
    CheckEndsWith -->|False| NextHost["Check next host"]
    NextHost --> HostnameLoop
    
    CallProxyBypass --> ProxyBypassResult{"Result?"}
    ProxyBypassResult -->|True| ReturnTrueBypass
    ProxyBypassResult -->|False| ReturnFalse["Return False"]
    
    ReturnTrueBypass --> End["Bypass proxy"]
    ReturnTrue --> End
    ReturnFalse --> End2["Use proxy"]
```

**Diagram: Proxy Bypass Decision Logic**

Sources: [src/requests/utils.py:753-811]()

### No-Proxy Patterns

The `no_proxy` configuration supports multiple pattern types:

1. **Exact Hostname Match**: `example.com` matches `http://example.com`.
2. **Domain Suffix Match**: `.example.com` matches `http://api.example.com`.
3. **Hostname with Port**: `example.com:8080` matches only that specific port.
4. **IPv4 Address**: `192.168.1.1` matches that specific IP.
5. **CIDR Notation**: `192.168.0.0/24` matches any IP in that range.

Sources: [src/requests/utils.py:776-799](), [tests/test_utils.py:220-230]()

### CIDR Support Implementation

```mermaid
flowchart LR
    subgraph "CIDR Validation"
        Input["192.168.1.0/24"] --> Split["Split on '/'"]
        Split --> ValidateIP["is_ipv4_address()"]
        Split --> ValidateMask["Check mask 1-32"]
        ValidateIP --> Valid1{"Valid?"}
        ValidateMask --> Valid2{"Valid?"}
        Valid1 -->|Yes| Valid2
        Valid2 -->|Yes| ReturnTrue["is_valid_cidr() = True"]
    end
    
    subgraph "Address Matching"
        CheckAddr["address_in_network(ip, net)"] --> UnpackIP["struct.unpack('=L', socket.inet_aton(ip))"]
        UnpackIP --> UnpackNet["Unpack network address"]
        UnpackNet --> CalcMask["dotted_netmask(bits)"]
        CalcMask --> BitwiseAnd["(ipaddr & netmask) == (network & netmask)"]
        BitwiseAnd --> MatchResult["Return boolean"]
    end
    
    ReturnTrue -.->|"If valid"| CheckAddr
```

**Diagram: CIDR Validation and Matching**

The CIDR matching uses binary operations for efficient network range checking:
- `is_valid_cidr()`: Validates CIDR format at [src/requests/utils.py:707-728]().
- `address_in_network()`: Performs bitwise comparison at [src/requests/utils.py:670-682]().
- `dotted_netmask()`: Converts CIDR mask to netmask at [src/requests/utils.py:685-693]().

Sources: [src/requests/utils.py:670-728]()

## Proxy Selection Logic

### The select_proxy Function

The `select_proxy(url, proxies)` function at [src/requests/utils.py:826-849]() implements a priority-based proxy selection algorithm:

**Priority Order:**
1. `scheme://hostname` - Most specific (e.g., `http://api.example.com`)
2. `scheme` - Protocol-level (e.g., `http`)
3. `all://hostname` - Host-specific fallback
4. `all` - Global fallback

```mermaid
flowchart TD
    Start["select_proxy(url, proxies)"] --> Parse["urlparse(url)"]
    Parse --> NoHostname{"urlparts.hostname is None?"}
    
    NoHostname -->|Yes| CheckSchemeOnly["proxies.get(scheme, proxies.get('all'))"]
    NoHostname -->|No| BuildKeys["Build proxy_keys list"]
    
    BuildKeys --> Keys["['scheme://hostname', 'scheme', 'all://hostname', 'all']"]
    Keys --> Loop["For each key in proxy_keys"]
    
    Loop --> KeyInProxies{"key in proxies?"}
    KeyInProxies -->|Yes| ReturnProxy["Return proxies[key]"]
    KeyInProxies -->|No| NextKey["Check next key"]
    
    NextKey --> Loop
    CheckSchemeOnly --> ReturnResult["Return proxy or None"]
    ReturnProxy --> End["Proxy URL or None"]
    ReturnResult --> End
```

**Diagram: Proxy Selection Priority**

Sources: [src/requests/utils.py:826-849]()

## Platform-Specific Behavior

### Windows Registry Support

On Windows, the system falls back to Windows Internet Settings registry when environment variables are not set. This is handled by `proxy_bypass_registry` at [src/requests/utils.py:99-135]().

```mermaid
flowchart TD
    Windows["proxy_bypass(host) on Windows"] --> CheckEnv{"getproxies_environment()?"}
    
    CheckEnv -->|Has env| UseEnv["proxy_bypass_environment(host)"]
    CheckEnv -->|No env| Registry["proxy_bypass_registry(host)"]
    
    Registry --> OpenKey["winreg.OpenKey(HKCU, Internet Settings)"]
    OpenKey --> ReadEnable["Read ProxyEnable value"]
    ReadEnable --> ReadOverride["Read ProxyOverride value"]
    
    ReadOverride --> CheckEnabled{"ProxyEnable == 1?"}
    CheckEnabled -->|No| ReturnFalse["Return False"]
    CheckEnabled -->|Yes| ParseOverride["Split ProxyOverride by ';'"]
    
    ParseOverride --> CheckLocal{"Entry == '<local>'?"}
    CheckLocal -->|Yes| NoDot{"'.' not in host?"}
    NoDot -->|Yes| ReturnTrue["Return True"]
    
    CheckLocal -->|No| RegexMatch["Convert wildcards to regex"]
    RegexMatch --> Match{"re.match(pattern, host)?"}
    Match -->|Yes| ReturnTrue
    Match -->|No| NextEntry["Check next entry"]
    
    NextEntry --> ParseOverride
    ReturnTrue --> End["Bypass proxy"]
    ReturnFalse --> End2["Use proxy"]
    UseEnv --> End3["Platform env result"]
```

**Diagram: Windows Proxy Bypass Logic**

The Windows implementation supports the `<local>` keyword and wildcard patterns (converting `*` to `.*` and `?` to `.`).

Sources: [src/requests/utils.py:96-147]()

## Integration with Session and Adapters

### The resolve_proxies Function

The `resolve_proxies(request, proxies, trust_env=True)` function at [src/requests/utils.py:852-876]() is the high-level interface used to merge explicit settings with the environment.

```mermaid
flowchart LR
    subgraph "Session Layer"
        Session["Session.request()"] --> MergeEnv["Session.merge_environment_settings()"]
    end
    
    subgraph "Proxy Resolution"
        MergeEnv --> ResolveProxies["resolve_proxies(request, proxies, trust_env)"]
        ResolveProxies --> CopyProxies["new_proxies = proxies.copy()"]
        CopyProxies --> CheckTrust{"trust_env?"}
        CheckTrust -->|Yes| ShouldBypass["should_bypass_proxies(url, no_proxy)"]
        ShouldBypass -->|False| GetEnv["get_environ_proxies(url, no_proxy)"]
        GetEnv --> SetDefault["new_proxies.setdefault(scheme, proxy)"]
        CheckTrust -->|No| ReturnCopy["Return new_proxies"]
        SetDefault --> ReturnCopy
    end
    
    subgraph "Adapter Layer"
        ReturnCopy --> Send["HTTPAdapter.send(request, proxies=...)"]
    end
```

**Diagram: Proxy Resolution in Request Flow**

Key behaviors:
- **trust_env=True** (default): Merges environment proxies with explicit proxies.
- **trust_env=False**: Uses only explicit proxies, ignores environment.
- Explicit proxies take precedence over environment proxies via `setdefault()`.

Sources: [src/requests/utils.py:852-876]()

## Key Functions Reference

| Function | Location | Purpose |
|----------|----------|---------|
| `resolve_proxies()` | [src/requests/utils.py:852-876]() | High-level proxy resolution entry point |
| `should_bypass_proxies()` | [src/requests/utils.py:753-811]() | Determines if proxy should be bypassed |
| `get_environ_proxies()` | [src/requests/utils.py:814-823]() | Retrieves proxies from environment |
| `select_proxy()` | [src/requests/utils.py:826-849]() | Selects appropriate proxy for URL |
| `address_in_network()` | [src/requests/utils.py:670-682]() | Checks if IP is in CIDR range |
| `is_valid_cidr()` | [src/requests/utils.py:707-728]() | Validates CIDR notation |
| `is_ipv4_address()` | [src/requests/utils.py:696-704]() | Validates IPv4 address |
| `dotted_netmask()` | [src/requests/utils.py:685-693]() | Converts CIDR mask to dotted notation |
| `proxy_bypass_registry()` | [src/requests/utils.py:99-135]() | Windows registry proxy bypass |

Sources: [src/requests/utils.py:96-876]()

---

# Page: Content Encoding Detection

# Content Encoding Detection

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [src/requests/models.py](src/requests/models.py)
- [src/requests/utils.py](src/requests/utils.py)
- [tests/test_lowlevel.py](tests/test_lowlevel.py)
- [tests/test_testserver.py](tests/test_testserver.py)
- [tests/test_utils.py](tests/test_utils.py)

</details>



## Purpose and Scope

This page documents the character encoding detection mechanisms used by the Requests library to decode HTTP response content into text. The library employs multiple detection strategies including HTTP header analysis, content inspection, and optional integration with character detection libraries (`charset_normalizer` or `chardet`).

For information about custom data structures used in encoding operations, see [Custom Data Structures](5.1). For proxy resolution and other utility functions, see [Proxy Resolution](5.2).

---

## Overview

Requests determines character encoding through a multi-stage detection process that prioritizes explicit declarations over heuristics. The detection strategy varies depending on content type and available metadata.

### Encoding Resolution Data Flow

Title: Encoding Detection Flow
```mermaid
graph TB
    Response["Response Object<br/>response.text property"]
    Headers["Check HTTP Headers<br/>get_encoding_from_headers()"]
    Content["Inspect Content<br/>get_encodings_from_content()"]
    JSON["JSON UTF Detection<br/>guess_json_utf()"]
    CharDet["Character Detection Libraries<br/>charset_normalizer/chardet"]
    Fallback["Fallback Encoding<br/>utf-8 or ISO-8859-1"]
    
    Response --> Headers
    Headers -->|"charset found"| Decode["Decode Content"]
    Headers -->|"no charset"| Content
    Content -->|"meta tags found"| Decode
    Content -->|"JSON content"| JSON
    Content -->|"no hints"| CharDet
    JSON --> Decode
    CharDet -->|"detected"| Decode
    CharDet -->|"not available"| Fallback
    Fallback --> Decode
```

**Detection Priority:**
1. Explicit `charset` parameter in `Content-Type` header.
2. HTML/XML meta declarations in content (via `get_encodings_from_content`).
3. JSON UTF encoding detection via BOM or null byte patterns (via `guess_json_utf`).
4. Character detection libraries (if available via `compat.chardet`).
5. Default fallbacks based on content type.

Sources: [src/requests/utils.py:532-555](), [src/requests/utils.py:482-504](), [src/requests/utils.py:950-979]()

---

## Header-Based Detection

The primary encoding detection mechanism examines the `Content-Type` HTTP header for a `charset` parameter. This is handled by utility functions that parse and extract encoding information.

### Content-Type Header Parsing

The `_parse_content_type_header()` function parses `Content-Type` headers into their components:

Title: Content-Type Parsing Logic
```mermaid
graph LR
    Input["Content-Type Header<br/>'application/json; charset=utf-8'"]
    Parse["_parse_content_type_header()"]
    MediaType["Media Type<br/>'application/json'"]
    Params["Parameters Dict<br/>{'charset': 'utf-8'}"]
    
    Input --> Parse
    Parse --> MediaType
    Parse --> Params
```

**Parsing Rules:**
- Splits header on semicolons to separate media type from parameters [src/requests/utils.py:511-512]().
- Extracts key-value pairs from parameter list [src/requests/utils.py:515-519]().
- Strips quotes and whitespace from values [src/requests/utils.py:521-524]().
- Converts parameter names to lowercase [src/requests/utils.py:516-516]().
- Handles parameters without values (sets value to `True`) [src/requests/utils.py:518-519]().

Sources: [src/requests/utils.py:507-529](), [tests/test_utils.py:576-637]()

### Encoding Extraction Logic

The `get_encoding_from_headers()` function applies content-type-specific rules to determine the appropriate encoding:

Title: get_encoding_from_headers Logic
```mermaid
graph TD
    Start["get_encoding_from_headers(headers)"]
    GetCT["Extract 'content-type' header"]
    HasCT{"Content-Type<br/>exists?"}
    Parse["_parse_content_type_header()"]
    HasCharset{"'charset'<br/>in params?"}
    IsText{"'text' in<br/>media type?"}
    IsJSON{"'application/json'<br/>in media type?"}
    
    Start --> GetCT
    GetCT --> HasCT
    HasCT -->|"yes"| Parse
    HasCT -->|"no"| ReturnNone["return None"]
    Parse --> HasCharset
    HasCharset -->|"yes"| ReturnCharset["return charset<br/>(strip quotes)"]
    HasCharset -->|"no"| IsText
    IsText -->|"yes"| ReturnISO["return 'ISO-8859-1'"]
    IsText -->|"no"| IsJSON
    IsJSON -->|"yes"| ReturnUTF8["return 'utf-8'"]
    IsJSON -->|"no"| ReturnNone
```

**Encoding Rules:**

| Content-Type Pattern | Charset Parameter | Returned Encoding | Rationale |
|---------------------|-------------------|-------------------|-----------|
| Any | `charset=X` present | `X` (stripped) | Explicit declaration takes precedence [src/requests/utils.py:544-545]() |
| `text/*` | No charset | `ISO-8859-1` | RFC 2616 default for text [src/requests/utils.py:548-549]() |
| `application/json` | No charset | `utf-8` | RFC 4627 specifies UTF-8 for JSON [src/requests/utils.py:552-553]() |

Sources: [src/requests/utils.py:532-555](), [tests/test_utils.py:640-652]()

---

## Content-Based Detection

When HTTP headers don't specify an encoding, Requests can inspect the response content itself for encoding declarations embedded in HTML or XML.

### HTML and XML Meta Tag Extraction

The `get_encodings_from_content()` function uses regular expressions to find encoding declarations in markup:

Title: Markup Encoding Extraction
```mermaid
graph TB
    Content["Response Content<br/>(HTML/XML string)"]
    Function["get_encodings_from_content(content)"]
    
    CharsetRE["Charset Regex<br/>&lt;meta.*?charset=[\"']*(.+?)[\"'&gt;]"]
    PragmaRE["Pragma Regex<br/>&lt;meta.*?content=[\"']*;?charset=(.+?)[\"'&gt;]"]
    XMLRE["XML Regex<br/>^&lt;?xml.*?encoding=[\"']*(.+?)[\"'&gt;]"]
    
    Results["List of Found Encodings<br/>(ordered by precedence)"]
    
    Content --> Function
    Function --> CharsetRE
    Function --> PragmaRE
    Function --> XMLRE
    CharsetRE --> Results
    PragmaRE --> Results
    XMLRE --> Results
```

**Precedence Order:**
Encodings are returned in the order they are found in the content [src/requests/utils.py:503-504](). The function checks for:
1. HTML5 `<meta charset="...">` [src/requests/utils.py:483-483]()
2. HTML4 `<meta http-equiv="Content-type" content="...charset=...">` [src/requests/utils.py:484-486]()
3. XML declaration `<?xml ... encoding="..."?>` [src/requests/utils.py:487-487]()

Sources: [src/requests/utils.py:482-504](), [tests/test_utils.py:373-403]()

---

## JSON UTF Encoding Detection

For JSON content, Requests includes specialized logic to detect UTF encoding variants by analyzing byte order marks (BOMs) and null byte patterns.

### Detection Algorithm

The `guess_json_utf()` function examines the first 4 bytes to determine encoding:

Title: guess_json_utf Logic
```mermaid
graph TD
    Start["guess_json_utf(data)"]
    Sample["Extract first 4 bytes"]
    
    CheckBOM32["Check for<br/>UTF-32 BOM"]
    CheckBOM8["Check for<br/>UTF-8 BOM"]
    CheckBOM16["Check for<br/>UTF-16 BOM"]
    CountNulls["Count null bytes"]
    
    Is32{"BOM_UTF32_LE or<br/>BOM_UTF32_BE?"}
    Is8{"First 3 bytes<br/>== BOM_UTF8?"}
    Is16{"First 2 bytes<br/>== BOM_UTF16?"}
    
    NullCount{"Null count?"}
    Check2Nulls["Analyze positions<br/>of 2 nulls"]
    Check3Nulls["Analyze positions<br/>of 3 nulls"]
    
    Start --> Sample
    Sample --> CheckBOM32
    CheckBOM32 --> Is32
    Is32 -->|"yes"| Return32["return 'utf-32'"]
    Is32 -->|"no"| CheckBOM8
    CheckBOM8 --> Is8
    Is8 -->|"yes"| Return8sig["return 'utf-8-sig'"]
    Is8 -->|"no"| CheckBOM16
    CheckBOM16 --> Is16
    Is16 -->|"yes"| Return16["return 'utf-16'"]
    Is16 -->|"no"| CountNulls
    CountNulls --> NullCount
    NullCount -->|"0"| Return8["return 'utf-8'"]
    NullCount -->|"2"| Check2Nulls
    NullCount -->|"3"| Check3Nulls
    NullCount -->|"other"| ReturnNone["return None"]
    
    Check2Nulls -->|"1st and 3rd null"| Return16BE["return 'utf-16-be'"]
    Check2Nulls -->|"2nd and 4th null"| Return16LE["return 'utf-16-le'"]
    
    Check3Nulls -->|"first 3 null"| Return32BE["return 'utf-32-be'"]
    Check3Nulls -->|"last 3 null"| Return32LE["return 'utf-32-le'"]
```

Sources: [src/requests/utils.py:950-979](), [tests/test_utils.py:405-437]()

---

## Character Detection Library Integration

When encoding cannot be determined from headers or content inspection, Requests optionally uses character detection libraries.

### Library Resolution

The `_resolve_char_detection()` function in `compat.py` attempts to import available character detection libraries:

Title: Character Detection Resolution
```mermaid
graph LR
    Start["_resolve_char_detection()"]
    TryChardet["Try import 'chardet'"]
    TryNormalizer["Try import 'charset_normalizer'"]
    SuccessChardet{"Import<br/>successful?"}
    SuccessNormalizer{"Import<br/>successful?"}
    ReturnLib["Return library module"]
    ReturnNone["Return None"]
    
    Start --> TryChardet
    TryChardet --> SuccessChardet
    SuccessChardet -->|"yes"| ReturnLib
    SuccessChardet -->|"no"| TryNormalizer
    TryNormalizer --> SuccessNormalizer
    SuccessNormalizer -->|"yes"| ReturnLib
    SuccessNormalizer -->|"no"| ReturnNone
```

**Library Priority:**
Requests searches for supported libraries in a specific order within `_resolve_char_detection`:
1. **`chardet`** - Checked first [src/requests/compat.py:39-42]().
2. **`charset_normalizer`** - Checked if `chardet` is missing [src/requests/compat.py:39-42]().

The result is assigned to `compat.chardet` [src/requests/compat.py:51-51]().

Sources: [src/requests/compat.py:36-51]()

---

## Encoding Detection Function Reference

### get_encoding_from_headers()
**Location:** [src/requests/utils.py:532-555]()
Extracts charset from `Content-Type` or applies defaults for `text` (`ISO-8859-1`) and `application/json` (`utf-8`).

### _parse_content_type_header()
**Location:** [src/requests/utils.py:507-529]()
Parses a `Content-Type` string into a media type and a dictionary of parameters.

### get_encodings_from_content()
**Location:** [src/requests/utils.py:482-504]()
Searches for meta tags and XML declarations. Note: Emits a `DeprecationWarning` suggesting the use of `charset_normalizer` or `beautifulsoup4` for more robust parsing [src/requests/utils.py:490-498]().

### guess_json_utf()
**Location:** [src/requests/utils.py:950-979]()
Detects UTF-8, UTF-16, and UTF-32 variants in JSON byte strings using BOMs and null-byte heuristics.

Sources: [src/requests/utils.py:482-979]()

---

# Page: Error Handling

# Error Handling

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [AUTHORS.rst](AUTHORS.rst)
- [docs/api.rst](docs/api.rst)
- [docs/user/advanced.rst](docs/user/advanced.rst)
- [docs/user/quickstart.rst](docs/user/quickstart.rst)
- [src/requests/_internal_utils.py](src/requests/_internal_utils.py)
- [src/requests/exceptions.py](src/requests/exceptions.py)
- [src/requests/hooks.py](src/requests/hooks.py)
- [tests/test_requests.py](tests/test_requests.py)

</details>



This document covers the error handling system in the Requests library, explaining how exceptions are structured, when they're raised, and how to handle them effectively in your code.

## Overview of Error Handling in Requests

Requests provides a comprehensive exception system that helps you identify and handle various error conditions that can occur during HTTP requests. All exceptions in Requests are designed to be descriptive and provide useful information about what went wrong.

The library follows a hierarchical exception structure that allows you to catch specific error types or broader categories depending on your needs. In version 2.x, `RequestException` was changed to subclass `IOError` (rather than `RuntimeError`) to more accurately categorize the type of error [docs/api.rst:223-227]().

Sources:
- [src/requests/exceptions.py:20-23]()
- [docs/api.rst:223-227]()

## Exception Hierarchy

Requests organizes exceptions in a hierarchy, allowing you to catch specific or general exception types as needed. All Requests-specific exceptions inherit from `RequestException` [src/requests/exceptions.py:20-27]().

### Exception Tree

```mermaid
graph TD
    IOError["IOError"]
    RequestException["RequestException"]
    ConnectionError["ConnectionError"]
    HTTPError["HTTPError"]
    Timeout["Timeout"]
    TooManyRedirects["TooManyRedirects"]
    ContentDecodingError["ContentDecodingError"]
    ChunkedEncodingError["ChunkedEncodingError"]
    InvalidURL["InvalidURL"]
    MissingSchema["MissingSchema"]
    InvalidSchema["InvalidSchema"]
    InvalidProxyURL["InvalidProxyURL"]
    SSLError["SSLError"]
    ProxyError["ProxyError"]
    ConnectTimeout["ConnectTimeout"]
    ReadTimeout["ReadTimeout"]
    JSONDecodeError["JSONDecodeError"]
    RetryError["RetryError"]
    InvalidHeader["InvalidHeader"]
    UnrewindableBodyError["UnrewindableBodyError"]
    StreamConsumedError["StreamConsumedError"]
    InvalidJSONError["InvalidJSONError"]
    
    IOError --> RequestException
    RequestException --> ConnectionError
    RequestException --> HTTPError
    RequestException --> Timeout
    RequestException --> TooManyRedirects
    RequestException --> ContentDecodingError
    RequestException --> ChunkedEncodingError
    RequestException --> InvalidURL
    RequestException --> MissingSchema
    RequestException --> InvalidSchema
    RequestException --> InvalidJSONError
    RequestException --> RetryError
    RequestException --> InvalidHeader
    RequestException --> UnrewindableBodyError
    RequestException --> StreamConsumedError
    
    InvalidJSONError --> JSONDecodeError
    
    ConnectionError --> SSLError
    ConnectionError --> ProxyError
    ConnectionError --> ConnectTimeout
    
    Timeout --> ConnectTimeout
    Timeout --> ReadTimeout
    
    InvalidURL --> InvalidProxyURL
```

Sources:
- [src/requests/exceptions.py:20-148]()
- [docs/api.rst:31-38]()

## Common Error Scenarios and Handling

### Network and Connection Errors
When network problems occur (DNS failures, refused connections), Requests raises a `ConnectionError` [src/requests/exceptions.py:70-72](). Specialized connection errors include `ProxyError` and `SSLError` [src/requests/exceptions.py:74-79]().

### HTTP Errors and `raise_for_status`
Unsuccessful HTTP status codes (4XX or 5XX) do not automatically raise exceptions. To trigger an exception for these cases, use the `raise_for_status()` method on the `Response` object, which raises an `HTTPError` [docs/user/quickstart.rst:160-165]().

### Timeouts
The `Timeout` exception is a base class for `ConnectTimeout` (failure to establish a connection) and `ReadTimeout` (server fails to send data within the allotted time) [src/requests/exceptions.py:82-99](). Catching `Timeout` will catch both subtypes. `ConnectTimeout` errors are generally safe to retry [src/requests/exceptions.py:91-95]().

### Redirect Errors
When a request exceeds the maximum number of redirections (configured via `max_redirects` on a `Session`), a `TooManyRedirects` exception is raised [src/requests/exceptions.py:106-108]().

### URL and Schema Validation
Requests performs basic validation on URLs before dispatching.
- `MissingSchema`: Raised when a URL lacks a protocol (e.g., "localhost:8000") [src/requests/exceptions.py:110-112]().
- `InvalidSchema`: Raised for unsupported protocols [src/requests/exceptions.py:114-116]().
- `InvalidURL`: Raised for malformed URLs [src/requests/exceptions.py:118-120]().

Sources:
- [src/requests/exceptions.py:70-120]()
- [docs/user/quickstart.rst:160-165]()
- [tests/test_requests.py:99-114]()

## Error Flow Diagram

This diagram maps the logical flow from a user request to potential code entities that handle or raise errors.

```mermaid
sequenceDiagram
    participant User as "User Code"
    participant Session as "requests.sessions.Session"
    participant Adapter as "requests.adapters.HTTPAdapter"
    participant Lib as "urllib3.PoolManager"

    User->>Session: "get(url, timeout=5)"
    Session->>Adapter: "send(PreparedRequest)"
    
    alt DNS/Socket Error
        Adapter->>Lib: "urlopen()"
        Lib--xAdapter: "urllib3.exceptions.HTTPError"
        Adapter->>User: "raise requests.exceptions.ConnectionError"
    else Connection Timeout
        Adapter->>Lib: "urlopen(timeout=5)"
        Lib--xAdapter: "urllib3.exceptions.ConnectTimeoutError"
        Adapter->>User: "raise requests.exceptions.ConnectTimeout"
    else SSL Failure
        Adapter->>Lib: "cert verify"
        Lib--xAdapter: "urllib3.exceptions.SSLError"
        Adapter->>User: "raise requests.exceptions.SSLError"
    else 4xx/5xx Response
        Adapter->>User: "return requests.models.Response (status=404)"
        User->>User: "Response.raise_for_status()"
        User->>User: "raise requests.exceptions.HTTPError"
    end
```

Sources:
- [src/requests/exceptions.py:20-148]()
- [docs/user/quickstart.rst:160-165]()
- [src/requests/sessions.py:635-655]()
- [src/requests/adapters.py:428-510]()

## Exception Details and Attributes

The base `RequestException` class is designed to store the context of the failure, specifically the `request` and `response` objects involved [src/requests/exceptions.py:28-35]().

| Attribute | Type | Description |
| :--- | :--- | :--- |
| `e.request` | `PreparedRequest` | The request object that was being processed [src/requests/exceptions.py:32](). |
| `e.response` | `Response` | The response received (if any) before the error occurred [src/requests/exceptions.py:30-31](). |

### JSONDecodeError Implementation
`JSONDecodeError` is a specialized exception that inherits from both `InvalidJSONError` and the environment's native `JSONDecodeError` (via `compat.py`) [src/requests/exceptions.py:42-43](). This ensures compatibility across different Python JSON backends while remaining catchable as a `RequestException`. It implements `__reduce__` to preserve pickling behavior from the underlying JSON library [src/requests/exceptions.py:55-63]().

Sources:
- [src/requests/exceptions.py:28-63]()
- [tests/test_requests.py:23-31]()

## Advanced Error Handling Best Practices

### 1. Always Set Explicit Timeouts
By default, Requests does not time out. A server that accepts a connection but never sends data can hang your application indefinitely. Use a tuple for `(connect_timeout, read_timeout)` for fine-grained control [src/requests/exceptions.py:91-99]().

### 2. Contextual Error Handling
Catch `RequestException` for a "catch-all" safety net, but handle specific failures like `Timeout` if you intend to implement retry logic.

```python
import requests
from requests.exceptions import RequestException, Timeout, HTTPError

try:
    r = requests.get('https://api.github.com', timeout=(3.05, 27))
    r.raise_for_status()
except Timeout:
    # Maybe retry the request?
    pass
except HTTPError as err:
    # Handle 4xx/5xx specifically
    print(f"HTTP error: {err}")
except RequestException as e:
    # Ambiguous error
    print(f"Fatal error: {e}")
```

### 3. Cleaning Up with Sessions
When an exception occurs within a `Session` block, the session should still be closed to release connection pool resources. Using a context manager (`with requests.Session() as s:`) handles this automatically even if unhandled exceptions occur [docs/user/advanced.rst:67-73]().

### 4. Handling Content Decoding Errors
If the server sends a malformed body or uses an unsupported compression format, Requests raises `ContentDecodingError` [src/requests/exceptions.py:134-135](). This is common when headers claim `gzip` but the body is plain text.

### 5. Header Validation
Requests uses internal regex validators to ensure header names and values are well-formed. Providing invalid header values can trigger an `InvalidHeader` exception [src/requests/_internal_utils.py:13-23]() [src/requests/exceptions.py:122-123]().

Sources:
- [src/requests/exceptions.py:82-148]()
- [docs/user/advanced.rst:67-73]()
- [docs/user/quickstart.rst:150-165]()
- [src/requests/_internal_utils.py:13-23]()

---

# Page: Development Guide

# Development Guide

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.coveragerc](.coveragerc)
- [.github/AI_POLICY.md](.github/AI_POLICY.md)
- [.github/CODE_OF_CONDUCT.md](.github/CODE_OF_CONDUCT.md)
- [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md)
- [.github/ISSUE_TEMPLATE.md](.github/ISSUE_TEMPLATE.md)
- [.gitignore](.gitignore)
- [Makefile](Makefile)
- [docs/dev/contributing.rst](docs/dev/contributing.rst)
- [docs/user/install.rst](docs/user/install.rst)

</details>



This document provides a high-level overview for developers and contributors working on the Requests library. It outlines the environment setup, contribution workflows, and the various systems used to maintain the project's quality and stability.

## Build and Test

Requests uses a `Makefile` to orchestrate common development tasks such as environment initialization, testing, and distribution. The project relies on `pytest` for its test suite.

*   **Initialization**: `make init` installs development dependencies from `requirements-dev.txt` [Makefile:2-3]().
*   **Testing**: The `make test` command executes the test suite located in the `tests/` directory [Makefile:4-5]().
*   **Coverage**: Code coverage is tracked using `pytest-cov`, with configurations defined in `.coveragerc` [Makefile:13-14](), [.coveragerc:1-2]().
*   **Publishing**: The build process creates a virtual environment `.publishenv` to handle distribution via `build` and `twine` [Makefile:16-23]().

For detailed information on the build system and test infrastructure, see [Build and Test](#7.1).

### Test Infrastructure Overview

```mermaid
graph TD
    subgraph "Entry Points"
        M_INIT["make init"]
        M_TEST["make test"]
        M_COV["make coverage"]
        M_PUB["make publish"]
    end

    subgraph "Execution Layer"
        PYTEST["python -m pytest"]
        PIP["python -m pip"]
        BUILD["python -m build"]
        TWINE["python -m twine"]
    end

    subgraph "Code Entities"
        TEST_DIR["tests/"]
        REQ_DEV["requirements-dev.txt"]
        SRC_REQ["src/requests/"]
        PUB_ENV[".publishenv"]
    end

    M_INIT --> PIP
    PIP --> REQ_DEV
    M_TEST --> PYTEST
    M_COV --> PYTEST
    M_PUB --> PUB_ENV
    PUB_ENV --> BUILD
    PUB_ENV --> TWINE
    PYTEST --> TEST_DIR
    PYTEST -- "calculates coverage for" --> SRC_REQ
```
Sources: [Makefile:2-23](), [.coveragerc:1-2]()

## CI/CD Pipeline

The project utilizes GitHub Actions for continuous integration. Every Pull Request and commit to the main branch triggers automated workflows to ensure code quality and prevent regressions.

*   **Automation**: Workflows handle linting, security scanning, and running the test suite across different operating systems and Python versions [Makefile:7-8]().
*   **Quality Gates**: CI results are used during the code review process to validate contributions. Formatting is enforced via `pre-commit` [docs/dev/contributing.rst:87-101]().
*   **Policies**: Contributions must adhere to the Generative AI policy, ensuring human authorship and technical accountability [.github/AI_POLICY.md:1-28]().

For details on the automated workflows and publishing process, see [CI/CD Pipeline](#7.2).

## Project Documentation

Requests documentation is authored in reStructuredText (`.rst`) and generated using Sphinx. The documentation source files are organized within the `docs/` directory.

*   **Build Process**: Documentation is generated locally using `make docs`, which triggers the Sphinx build system [Makefile:25-27]().
*   **Style**: Documentation follows a semi-formal, approachable prose style with a 79-character line limit [docs/dev/contributing.rst:122-132]().

For details on the documentation structure and configuration, see [Project Documentation](#7.3).

### Documentation Mapping

```mermaid
graph LR
    subgraph "Natural Language Space"
        USER_GUIDE["User Guides"]
        DEV_GUIDE["Contributor Guide"]
        INSTALL_DOC["Installation"]
        AI_POLICY["AI Usage Policy"]
    end

    subgraph "Code Entity Space"
        USER_DIR["docs/user/*.rst"]
        CONTRIB_RST["docs/dev/contributing.rst"]
        INSTALL_RST["docs/user/install.rst"]
        AI_MD[".github/AI_POLICY.md"]
    end

    subgraph "Output"
        HTML["docs/_build/html/index.html"]
    end

    USER_GUIDE --> USER_DIR
    DEV_GUIDE --> CONTRIB_RST
    INSTALL_DOC --> INSTALL_RST
    AI_POLICY --> AI_MD
    USER_DIR --> HTML
    CONTRIB_RST --> HTML
    INSTALL_RST --> HTML
```
Sources: [docs/dev/contributing.rst:1-4](), [docs/user/install.rst:1-6](), [Makefile:25-27](), [.github/AI_POLICY.md:1-5]()

## Security Management

The project maintains a rigorous approach to security, including clear guidelines for reporting vulnerabilities and managing advisories.

*   **Bug Reports**: Security-related bugs should be investigated against both open and closed issues before filing [docs/dev/contributing.rst:140-149]().
*   **System Info**: Contributors are encouraged to provide system context using `python -m requests.help` when reporting issues [.github/ISSUE_TEMPLATE.md:18-28]().
*   **Conduct**: All contributors must follow the Python Software Foundation Code of Conduct [docs/dev/contributing.rst:25-35](), [.github/CODE_OF_CONDUCT.md:1-6]().

For documentation on the vulnerability disclosure process and security advisory workflow, see [Security Management](#7.4).

## Contribution Workflow

Requests follows a standard fork-and-pull-request model on GitHub [docs/dev/contributing.rst:65-81]().

| Phase | Description | Reference |
| :--- | :--- | :--- |
| **Feedback** | Seek feedback early, even for unfinished work. | [docs/dev/contributing.rst:39-47]() |
| **Development** | Fork, clone, write failing tests, and implement fixes. | [docs/dev/contributing.rst:65-81]() |
| **AI Policy** | Ensure changes are human-authored and fully understood. | [.github/AI_POLICY.md:52-72]() |
| **Standards** | Use `pre-commit` hooks for formatting and linting. | [docs/dev/contributing.rst:96-107]() |
| **Review** | Maintainers review all code before merging. | [docs/dev/contributing.rst:87-94]() |

### Policy on New Features
Requests is currently in a perpetual feature freeze. The maintainers believe the library is feature-complete, and new features are rarely accepted without approval from the BDFL [docs/dev/contributing.rst:152-162]().

Sources: [docs/dev/contributing.rst:39-165](), [Makefile:2-27](), [.github/AI_POLICY.md:1-72](), [.github/CONTRIBUTING.md:1-66]()

---

# Page: Build and Test

# Build and Test

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.coveragerc](.coveragerc)
- [.github/ISSUE_TEMPLATE.md](.github/ISSUE_TEMPLATE.md)
- [.gitignore](.gitignore)
- [Makefile](Makefile)
- [pyproject.toml](pyproject.toml)
- [requirements-dev.txt](requirements-dev.txt)
- [setup.py](setup.py)
- [tests/__init__.py](tests/__init__.py)
- [tests/compat.py](tests/compat.py)
- [tests/conftest.py](tests/conftest.py)
- [tests/test_help.py](tests/test_help.py)
- [tests/testserver/__init__.py](tests/testserver/__init__.py)
- [tests/testserver/server.py](tests/testserver/server.py)
- [tox.ini](tox.ini)

</details>



This document provides comprehensive information about the build system and testing infrastructure for the Requests library. It covers how to set up a development environment, run tests, check code quality, and build documentation using the project's standardized tools.

## Development Environment Setup

Requests uses a `pyproject.toml` file for modern package metadata and build configuration, while maintaining a `Makefile` for developer convenience and a `setup.py` for legacy compatibility.

### Prerequisites

- Python 3.10 or later [setup.py:3-5](), [pyproject.toml:17]()
- pip
- Git

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/psf/requests.git
   cd requests
   ```

2. Install development dependencies:
   ```bash
   make init
   ```
   
   This command installs all development dependencies listed in `requirements-dev.txt`, which includes `pytest`, `httpbin`, and `trustme` [Makefile:2-3](), [requirements-dev.txt:1-7]().

Sources: [Makefile:2-3](), [requirements-dev.txt:1-7](), [pyproject.toml:17](), [setup.py:3-5]()

## Build System Configuration

The project utilizes `setuptools` as the build backend [pyproject.toml:1-3]().

| File | Role |
|------|------|
| `pyproject.toml` | Defines build system requirements, project metadata, and tool configurations (Ruff, Pytest, Pyright) [pyproject.toml:1-125]() |
| `setup.py` | Minimal wrapper that calls `setup()` to support legacy build environments [setup.py:7-9]() |
| `Makefile` | Orchestrates development tasks like testing, coverage, and publishing [Makefile:1-27]() |
| `tox.ini` | Configures multi-environment testing across Python versions 3.10 through 3.14 [tox.ini:1-18]() |

Sources: [pyproject.toml:1-125](), [setup.py:1-9](), [Makefile:1-27](), [tox.ini:1-18]()

## Testing Infrastructure

Requests employs a robust testing suite designed to verify HTTP behavior against real and mocked endpoints.

### Core Testing Components

```mermaid
graph TD
    subgraph "Test_Execution"
        pytest["pytest"]
        tox["tox"]
        coverage["pytest-cov"]
    end
    
    subgraph "Mocking_and_Servers"
        httpbin["pytest-httpbin / httpbin"]
        trustme["trustme (SSL Certs)"]
        Server["tests.testserver.server.Server"]
    end
    
    subgraph "Code_Quality"
        ruff["Ruff (Lint/Format)"]
        pyright["Pyright (Types)"]
    end
    
    tox -->|"Orchestrates"| pytest
    pytest -->|"Uses"| httpbin
    pytest -->|"Uses"| trustme
    pytest -->|"Uses"| Server
    pytest -->|"Reports"| coverage
```

Sources: [pyproject.toml:58-75](), [tox.ini:1-10](), [requirements-dev.txt:2-6](), [tests/testserver/server.py:25-50]()

### Test Fixtures and Configuration

The `tests/conftest.py` file defines essential fixtures for the test suite:

- **`clean_proxy_environ`**: Automatically removes proxy environment variables (e.g., `http_proxy`, `no_proxy`) before every test to ensure a clean state by using `monkeypatch.delenv` [tests/conftest.py:25-32]().
- **`httpbin` / `httpbin_secure`**: Wrappers around `pytest-httpbin` that ensure URLs have trailing slashes via the `prepare_url` helper [tests/conftest.py:15-23](), [tests/conftest.py:34-41]().
- **`nosan_server`**: Spawns a local `HTTPServer` using `trustme` to generate a certificate with only a `commonName` and no `subjectAltName`, specifically for testing SSL verification edge cases. It runs the server in a `threading.Thread` and yields the address and CA bundle [tests/conftest.py:44-67]().

### Test Environment Initialization

The `tests/__init__.py` file configures the global warning state for the test suite. Specifically, it ensures `SNIMissingWarning` from `urllib3` always fires during testing to validate HTTPS warning logic [tests/__init__.py:5-14]().

Sources: [tests/conftest.py:15-67](), [tests/__init__.py:1-14]()

## Internal Test Server

For low-level socket and TLS testing, Requests includes a custom `Server` implementation in `tests/testserver/server.py`.

- **`Server`**: A `threading.Thread` subclass that manages a raw socket. It uses `select.select` to handle connections and allows custom `handler` functions to process raw socket data [tests/testserver/server.py:25-50]().
- **`consume_socket_content`**: A utility function that reads all available data from a socket until a timeout or EOF is reached [tests/testserver/server.py:7-22]().
- **`TLSServer`**: A subclass of `Server` that wraps the socket in an `ssl.SSLContext`. It supports mutual TLS by loading a `cacert` and setting `verify_mode` to `ssl.CERT_OPTIONAL` [tests/testserver/server.py:138-170]().

Sources: [tests/testserver/server.py:7-176]()

## Running Tests

### Basic Execution
To run the standard test suite:
```bash
make test
```
This executes `python -m pytest tests` [Makefile:4-5]().

### Coverage Analysis
To generate coverage reports for the `src/requests` directory:
```bash
make coverage
```
This uses `.coveragerc` to omit internal packages and outputs both terminal and XML reports [Makefile:13-14](), [.coveragerc:1-2]().

### Multi-version Testing
Using `tox`, you can run tests across all supported Python versions (3.10 - 3.14) and configurations. The `use_chardet_on_py3` environment specifically tests with the `chardet` extra enabled [tox.ini:1-18]().

Sources: [Makefile:4-14](), [tox.ini:1-18](), [.coveragerc:1-2]()

## Code Entity to Test Mapping

This diagram associates specific codebase entities with their corresponding test infrastructure and internal utilities.

```mermaid
graph LR
    subgraph "Code_Entity_Space"
        S_Help["info() (requests.help)"]
        S_Server["Server (tests.testserver.server)"]
        S_TLSServer["TLSServer (tests.testserver.server)"]
    end

    subgraph "Test_Infrastructure"
        T_Httpbin["httpbin fixture (conftest.py)"]
        T_Nosan["nosan_server fixture (conftest.py)"]
        T_HelpTests["test_help.py"]
    end

    T_HelpTests -.->|"Validates output of"| S_Help
    T_Nosan -.->|"Implements similar logic to"| S_TLSServer
    T_Httpbin -.->|"Alternative to"| S_Server
```

Sources: [tests/conftest.py:34-67](), [tests/test_help.py:3-27](), [tests/testserver/server.py:25-176]()

## Linting and Static Analysis

The project uses **Ruff** for linting and formatting, and **Pyright** for type checking.

- **Ruff Configuration**: Target version is Python 3.10. It enforces rules for imports (`I`), pyupgrade (`UP`), and standard errors/warnings (`E`, `W`, `F`) [pyproject.toml:86-101](). It is configured to use double quotes and space indentation [pyproject.toml:106-110]().
- **Pyright Configuration**: Set to `strict` mode, focusing on the `src/requests` directory while ignoring certain private usage and unused import reports that overlap with Ruff [pyproject.toml:118-125]().

To check README/HISTORY markup:
```bash
make test-readme
```
This uses `setup.py check` to ensure valid RestructuredText for PyPI [Makefile:10-11]().

Sources: [pyproject.toml:86-125](), [Makefile:10-11]()

## Documentation and Publishing

### Documentation
Documentation is built using Sphinx:
```bash
make docs
```
This executes `make html` within the `docs` directory [Makefile:25-27]().

### Publishing
The publication process is automated via a virtual environment:
1. `make publish` creates a `.publishenv` and installs `twine` and `build` [Makefile:16-18]().
2. It builds the package using `python -m build` [Makefile:20-21]().
3. It uploads to PyPI using `twine` and cleans up the build artifacts [Makefile:22-23]().

Sources: [Makefile:16-27]()

---

# Page: CI/CD Pipeline

# CI/CD Pipeline

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.github/dependabot.yml](.github/dependabot.yml)
- [.github/workflows/codeql-analysis.yml](.github/workflows/codeql-analysis.yml)
- [.github/workflows/lint.yml](.github/workflows/lint.yml)
- [.github/workflows/lock-issues.yml](.github/workflows/lock-issues.yml)
- [.github/workflows/publish.yml](.github/workflows/publish.yml)
- [.github/workflows/run-tests.yml](.github/workflows/run-tests.yml)
- [.github/workflows/typecheck.yml](.github/workflows/typecheck.yml)
- [.github/workflows/zizmor.yml](.github/workflows/zizmor.yml)
- [.pre-commit-config.yaml](.pre-commit-config.yaml)

</details>



## Purpose and Scope

This document describes the Continuous Integration and Continuous Deployment (CI/CD) pipeline used for the Requests library. It covers the GitHub Actions workflows that automatically test, lint, and analyze the codebase, as well as automate issue management and package publishing to PyPI. For information about the build system and testing infrastructure specifically, see [Build and Test](#7.1).

## Overview

The Requests library uses GitHub Actions as its primary CI/CD platform. The pipeline consists of several workflows that run automatically on specific triggers such as code pushes, pull requests, scheduled times, or manual dispatches.

### Pipeline Architecture

```mermaid
graph TD
    subgraph "Triggers"
        Push["Code Push"]
        PR["Pull Request"]
        Schedule["Scheduled Events"]
        Manual["workflow_dispatch"]
        Tag["Version Tag (v*)"]
    end

    subgraph "Workflows"
        Push --> RunTests["run-tests.yml"]
        Push --> Lint["lint.yml"]
        Push --> TypeCheck["typecheck.yml"]
        Push --> CodeQL["codeql-analysis.yml"]
        Push --> Zizmor["zizmor.yml"]
        
        PR --> RunTests
        PR --> Lint
        PR --> TypeCheck
        PR --> CodeQL
        PR --> Zizmor
        
        Schedule --> ScheduledCodeQL["Scheduled CodeQL"]
        Schedule --> LockIssues["lock-issues.yml"]

        Manual --> Publish["publish.yml"]
        Tag --> Publish
    end

    subgraph "Jobs"
        RunTests --> TestMatrix["Test Matrix"]
        RunTests --> NoChardet["No Character Detection"]
        RunTests --> URLLib3["urllib3 1.x"]
        
        Lint --> PreCommitCheck["pre-commit"]
        TypeCheck --> Pyright["pyright"]
        
        CodeQL --> SecurityAnalysis["CodeQL Analyze"]
        Zizmor --> GhaSecurity["zizmor Security Analysis"]
        
        Publish --> BuildDists["Build dists"]
        BuildDists --> PyPI["Publish to PyPI"]
        BuildDists --> TestPyPI["Publish to Test PyPI"]
    end
```

Sources: [.github/workflows/run-tests.yml:1-3](), [.github/workflows/lint.yml:1-3](), [.github/workflows/typecheck.yml:1-3](), [.github/workflows/codeql-analysis.yml:6-15](), [.github/workflows/publish.yml:1-13](), [.github/workflows/zizmor.yml:1-9]()

## Testing Workflow

The primary testing workflow is defined in the `run-tests.yml` file and is responsible for running the test suite across multiple Python versions and operating systems.

### Test Matrix Strategy

The `build` job utilizes a strategy matrix to maximize environment coverage.

```mermaid
graph TD
    subgraph "run-tests.yml [Strategy Matrix]"
        OS["runs-on"]
        Python["python-version"]
    end
    
    OS --> U22["ubuntu-22.04"]
    OS --> Mac["macOS-latest"]
    OS --> Win["windows-latest"]
    
    Python --> P10["3.10"]
    Python --> P11["3.11"]
    Python --> P12["3.12"]
    Python --> P13["3.13"]
    Python --> P14["3.14"]
    Python --> P14t["3.14t"]
    Python --> P15dev["3.15-dev"]
    Python --> PyPy["pypy-3.11"]
    
    U22 --- P10
    Mac --- P11
    Win --- P12
```

Sources: [.github/workflows/run-tests.yml:12-20]()

### Main Test Job

The main test job (`build`) runs a matrix of tests across:
- **Python versions**: 3.10 through 3.15-dev, including experimental "t" (freethreading) builds and PyPy 3.11 [[.github/workflows/run-tests.yml:15-15]]().
- **Operating systems**: Ubuntu 22.04, macOS, and Windows [[.github/workflows/run-tests.yml:16-16]]().
- **Exclusions**: PyPy 3.11 is excluded on Windows due to OpenSSL/Rust installation constraints [[.github/workflows/run-tests.yml:17-20]]().

The job executes the following command sequence:
1. `make`: Installs dependencies [[.github/workflows/run-tests.yml:36-36]]().
2. `make ci`: Executes the test suite with coverage reporting [[.github/workflows/run-tests.yml:39-39]]().

### Special Test Cases

Two specialized test jobs verify specific compatibility scenarios:

1. **No Character Detection** (`no_chardet`): Uninstalls `charset_normalizer` and `chardet` before running tests to ensure the library handles missing optional dependencies gracefully [[.github/workflows/run-tests.yml:58-61]]().
2. **urllib3 1.x Compatibility** (`urllib3`): Specifically installs `urllib3<2` to verify backward compatibility with the older major version of the transport engine [[.github/workflows/run-tests.yml:80-83]]().

Sources: [.github/workflows/run-tests.yml:41-83]()

## Code Quality and Security Workflows

### Lint and Type Check Workflows

The project enforces code quality through linting and static type checking.

- **Lint Workflow**: Uses `pre-commit` (v4.6.0) on `ubuntu-24.04` [[.github/workflows/lint.yml:10-23]](). It runs hooks defined in `.pre-commit-config.yaml`, including `ruff-check` and `ruff-format` [[.pre-commit-config.yaml:18-20]]().
- **Type Check Workflow**: Runs `pyright` against the `src/requests/` directory across Python 3.10 and 3.14 [[.github/workflows/typecheck.yml:14, 32]]().

### Security Analysis

The project employs two distinct security scanning workflows:
1. **CodeQL**: Performs deep static analysis of the Python code to find vulnerabilities [[.github/workflows/codeql-analysis.yml:48-74]](). It runs on pushes to `main`, PRs, and a weekly schedule [[.github/workflows/codeql-analysis.yml:9-15]]().
2. **zizmor**: Analyzes the GitHub Actions workflow files themselves for security misconfigurations [[.github/workflows/zizmor.yml:23-24]]().

## Deployment and Publishing

The `publish.yml` workflow handles the distribution of the package to PyPI.

### Publishing Flow

```mermaid
graph TD
    subgraph "publish.yml"
        BuildJob["build job"]
        PublishPyPI["publish job"]
        PublishTest["publish-test-pypi job"]
    end

    BuildJob --> BuildStep["python -m build"]
    BuildStep --> Upload["upload-artifact (dist/)"]
    
    Upload --> Download["download-artifact"]
    Download --> PublishPyPI
    Download --> PublishTest

    TriggerTag["Tag v*"] --> PublishPyPI
    TriggerManual["workflow_dispatch"] --> PublishTest
```

Sources: [.github/workflows/publish.yml:18-95]()

- **Build**: Uses the `build` module (v1.4.0) to create distributions. It sets `SOURCE_DATE_EPOCH` to the timestamp of the last commit for reproducible builds [[.github/workflows/publish.yml:36-41]]().
- **PyPI**: Triggered by version tags (e.g., `v2.31.0`). It uses Trusted Publishing (OIDC) via `id-token: write` permissions and enables `attestations` [[.github/workflows/publish.yml:4-6, 57-57, 70-72]]().
- **Test PyPI**: Triggered manually via `workflow_dispatch` for verification [[.github/workflows/publish.yml:7-12, 74-76]]().

## Maintenance Automation

### Automatic Thread Locking
The `lock-threads` workflow runs daily to lock inactive issues and pull requests (inactive for 90 days) to prevent "graveyard" commenting [[.github/workflows/lock-issues.yml:5-19]]().

### Dependabot Integration
The project uses Dependabot to keep CI dependencies up to date. It is configured to:
- Check `github-actions` and `pre-commit` ecosystems weekly [[.github/dependabot.yml:3-21]]().
- Ignore patch updates to reduce noise [[.github/dependabot.yml:10-11]]().
- Group updates to minimize the number of pull requests [[.github/dependabot.yml:14-17]]().

Sources: [.github/dependabot.yml:1-30]()

---

# Page: Project Documentation

# Project Documentation

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.readthedocs.yaml](.readthedocs.yaml)
- [LICENSE](LICENSE)
- [NOTICE](NOTICE)
- [docs/Makefile](docs/Makefile)
- [docs/community/out-there.rst](docs/community/out-there.rst)
- [docs/community/support.rst](docs/community/support.rst)
- [docs/community/updates.rst](docs/community/updates.rst)
- [docs/conf.py](docs/conf.py)
- [docs/dev/authors.rst](docs/dev/authors.rst)
- [docs/make.bat](docs/make.bat)
- [docs/requirements.txt](docs/requirements.txt)

</details>



This document provides a comprehensive guide on the structure, tools, and processes for managing and building the Requests library documentation. If you're looking for information about the CI/CD pipeline, see [CI/CD Pipeline](7.2), or for instructions on building and testing the code itself, see [Build and Test](7.1).

## Documentation System Overview

The Requests library uses Sphinx as its documentation generation system. Documentation is written primarily in reStructuredText (RST) format and is built into HTML, PDF, and other formats using the Sphinx documentation generator [docs/conf.py:3-5]().

### Natural Language to Code Entity Mapping: Build System
The following diagram bridges high-level documentation concepts to the specific files and variables that implement them in the `requests` codebase.

```mermaid
graph TD
    subgraph "NaturalLanguageSpace"["Natural Language Space"]
        BuildCmd["Build Commands"]
        Theme["Visual Styling"]
        Metadata["Project Metadata"]
        Ext["Functional Extensions"]
    end

    subgraph "CodeEntitySpace"["Code Entity Space"]
        Makefile["docs/Makefile"]
        ConfPy["docs/conf.py"]
        Requirements["docs/requirements.txt"]
        
        BuildCmd --> Makefile
        BuildCmd --> Requirements
        Theme --> ConfPy
        Metadata --> ConfPy
        Ext --> ConfPy

        subgraph "EntitiesInConfPy"["Entities in docs/conf.py"]
            html_theme["html_theme = 'alabaster'"]
            extensions["extensions = [...]"]
            version_attr["version = requests.__version__"]
        end
        
        Theme -.-> html_theme
        Ext -.-> extensions
        Metadata -.-> version_attr
    end
```

Sources: [docs/conf.py:38-43](), [docs/conf.py:122-134](), [docs/Makefile:1-59](), [docs/requirements.txt:1-3]()

## Documentation File Structure

The Requests documentation is organized into a hierarchical structure within the `docs` directory. Understanding this structure is essential for making documentation changes.

```mermaid
graph TD
    subgraph "DocumentationDirectoryStructure"["Documentation Directory Structure"]
        docs["docs/"] --> community["community/"]
        docs --> dev["dev/"]
        docs --> _static["_static/"]
        docs --> _templates["_templates/"]
        docs --> conf["docs/conf.py"]
        docs --> Makefile["docs/Makefile"]
        docs --> requirements["docs/requirements.txt"]
        
        community --> outThere["docs/community/out-there.rst"]
        community --> support["docs/community/support.rst"]
        community --> updates["docs/community/updates.rst"]
        
        dev --> authors["docs/dev/authors.rst"]
        
        _templates --> sidebar["_templates/sidebar.html"]
        
        _static --> custom["_static/custom.css"]
    end
```

Sources: [docs/conf.py:46-57](), [docs/community/out-there.rst:1-10](), [docs/community/support.rst:1-31](), [docs/community/updates.rst:1-18](), [docs/dev/authors.rst:1-4](), [docs/requirements.txt:1-3](), [docs/Makefile:1-10]()

## Sphinx Configuration

The Sphinx documentation generator is configured through the `docs/conf.py` file, which specifies project information, extension modules, and output formatting details.

### Key Configuration Elements

| Configuration | Value | Purpose |
|---------------|-------|---------|
| `project` | `u"Requests"` | Displayed in documentation titles [docs/conf.py:60]() |
| `extensions` | `autodoc`, `intersphinx`, `todo`, `viewcode` | Enable Sphinx extensions [docs/conf.py:38-43]() |
| `templates_path` | `["_templates"]` | Location of custom templates [docs/conf.py:46]() |
| `source_suffix` | `".rst"` | File extension for documentation files [docs/conf.py:51]() |
| `html_theme` | `"alabaster"` | Theme used for HTML output [docs/conf.py:122]() |
| `version` | `requests.__version__` | Version dynamically pulled from code [docs/conf.py:69-71]() |
| `html_sidebars` | `sidebar.html`, `localtoc.html`, etc. | Custom sidebar layouts [docs/conf.py:174-183]() |
| `todo_include_todos`| `True` | Include todo items in final output [docs/conf.py:115]() |

The configuration explicitly adds the parent directory to `sys.path` to allow `autodoc` to import the `requests` package for API documentation [docs/conf.py:24-27]().

Sources: [docs/conf.py:24-184]()

## Building the Documentation

The documentation build process converts RST source files into various output formats. The project uses a `Makefile` for Unix systems and a `make.bat` for Windows to orchestrate the `sphinx-build` command.

### Build Logic Flow
This diagram shows how the build environment interacts with the source code to produce final documentation.

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Make as docs/Makefile
    participant Sphinx as sphinx-build
    participant Code as requests/__init__.py
    participant Out as _build/html

    Dev->>Make: make html
    Make->>Sphinx: Executing sphinx-build -b html
    Sphinx->>Code: Import requests to get __version__
    Note over Sphinx, Code: sys.path.insert(0, os.path.abspath(".."))
    Sphinx->>Sphinx: Process docs/conf.py
    Sphinx->>Sphinx: Parse .rst files
    Sphinx->>Out: Write HTML files
    Out-->>Dev: Review results
```

### Build Commands

To build the documentation locally:

1. **Install required dependencies**:
   The documentation requires specific versions of Sphinx, currently pinned to `7.2.6` [docs/requirements.txt:3]().
   ```bash
   pip install -r docs/requirements.txt
   ```

2. **Navigate to the docs directory**:
   ```bash
   cd docs
   ```

3. **Build HTML documentation**:
   The `Makefile` defines the `html` target which executes `$(SPHINXBUILD) -b html` [docs/Makefile:54-59](). On Windows, `make.bat` provides the same functionality [docs/make.bat:75-81]().
   ```bash
   make html
   ```

4. **View the results**:
   The output is generated in the `_build` directory, specifically `_build/html` for HTML builds [docs/Makefile:8-9]().

### Read the Docs Integration
The project is configured for automated builds on Read the Docs via `.readthedocs.yaml` [.readthedocs.yaml:1-5](). It uses Ubuntu 22.04 and Python 3.12 for the build environment [.readthedocs.yaml:9-11]() and triggers the `dirhtml` builder [.readthedocs.yaml:16](). It also builds PDF and ePub formats [.readthedocs.yaml:19-21]().

Sources: [docs/Makefile:1-184](), [docs/make.bat:1-240](), [docs/requirements.txt:1-3](), [docs/conf.py:24-28](), [.readthedocs.yaml:1-29]()

## Documentation Content Organization

The Requests documentation includes community resources, support information, and references to external integrations.

- **Integrations**: `docs/community/out-there.rst` tracks external articles, talks, and blog posts about the library [docs/community/out-there.rst:1-10]().
- **Support**: `docs/community/support.rst` provides directions for Stack Overflow, GitHub Issues, and social media support [docs/community/support.rst:1-31]().
- **Updates**: `docs/community/updates.rst` includes the project's `HISTORY.md` file to show a chronological changelog [docs/community/updates.rst:1-18]().
- **Authors**: `docs/dev/authors.rst` includes the top-level `AUTHORS.rst` file to list project contributors [docs/dev/authors.rst:1-4]().
- **Themes**: The documentation uses the `alabaster` theme but utilizes `flask_theme_support.FlaskyStyle` for syntax highlighting [docs/conf.py:106](), [docs/conf.py:122]().

Sources: [docs/community/out-there.rst:1-10](), [docs/community/support.rst:1-31](), [docs/community/updates.rst:1-18](), [docs/dev/authors.rst:1-4](), [docs/conf.py:106-134]()

## License and Copyright

The Requests documentation and project are protected under the **Apache License, Version 2.0** [LICENSE:2-3](). Copyright is held by Kenneth Reitz and contributors [docs/conf.py:61-62](). The project also includes a `NOTICE` file acknowledging the copyright [NOTICE:1-2]().

Sources: [LICENSE:1-130](), [NOTICE:1-2](), [docs/conf.py:59-62]()

---

# Page: Security Management

# Security Management

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.github/SECURITY.md](.github/SECURITY.md)
- [.github/workflows/codeql-analysis.yml](.github/workflows/codeql-analysis.yml)
- [docs/community/vulnerabilities.rst](docs/community/vulnerabilities.rst)

</details>



This document outlines the security management processes in the Requests library, including vulnerability disclosure procedures, security advisory workflows, and automated security analysis.

## Security Policy Overview

The Requests library maintains a comprehensive security policy that defines how vulnerabilities are handled and resolved. This policy establishes clear procedures for reporting, confirming, fixing, and disclosing security issues to ensure user safety and project integrity.

Sources: [.github/SECURITY.md:1-84](), [docs/community/vulnerabilities.rst:1-5]()

## Vulnerability Disclosure Process

### Reporting Security Vulnerabilities

Security vulnerabilities must be reported through GitHub's Security Advisory system rather than public issues to prevent premature exposure:

1.  **Draft Advisory**: Open a [draft Security Advisory](https://github.com/psf/requests/security/advisories/new) via GitHub [[.github/SECURITY.md:3-6]()].
2.  **Reproduction**: Provide detailed reproduction information, including the shortest amount of code necessary to demonstrate the issue [[.github/SECURITY.md:13-15]()].
3.  **Communication**: Specify the impact and problem details. If English is not the reporter's first language, the team encourages reporting in a native language to be translated via online services [[.github/SECURITY.md:8-11]()].

Vulnerability information remains confidential until a fix is available and properly released. The project team will retrieve a CVE identifier if necessary and provide full credit to the reporter [[.github/SECURITY.md:16-19]()].

Sources: [.github/SECURITY.md:1-23]()

### Response Timeline

The project adheres to the following timeline for addressing security vulnerabilities:

| Stage | Timeframe |
|-------|-----------|
| Initial response | Within 2 days (typically ≤12 hours) [[.github/SECURITY.md:33-35]()] |
| Vulnerability confirmation | After successful reproduction [[.github/SECURITY.md:38-41]()] |
| Fix development | Target of 2 weeks from initial disclosure [[.github/SECURITY.md:42-43]()] |
| Downstream notification | At least 1 week before release [[.github/SECURITY.md:69-70]()] |
| Release | On a weekday following notification period [[.github/SECURITY.md:57-57]()] |

Sources: [.github/SECURITY.md:31-57]()

## Security Advisory Workflow

When a security vulnerability is confirmed, the maintainers manage the resolution through a structured advisory workflow involving coordination with downstream packagers.

### Fix Development and Release

1.  **Private Development**: A fix is developed and tested within the secure GitHub advisory workspace.
2.  **CVE Coordination**: A CVE identifier is obtained only when a fix is ready for release [[.github/SECURITY.md:18-19]()].
3.  **Downstream Notification**: Major downstream packagers are notified at least one week in advance [[.github/SECURITY.md:69-70]()].
4.  **Release Execution**: The patched version is released on a weekday [[.github/SECURITY.md:57-57]()].
5.  **Public Disclosure**: The patch is pushed to the public repository, the `HISTORY.md` is updated with credits, and a PyPI release is issued [[.github/SECURITY.md:74-76]()].
6.  **Patch Transparency**: The project explicitly mentions which commits contain the fix to facilitate manual patching for users unable to upgrade immediately [[.github/SECURITY.md:82-84]()].

Sources: [.github/SECURITY.md:54-84]()

## Downstream Notification

Prior to security releases, the following maintainers receive advance notification of impending patches to ensure synchronized updates:
- **Python Maintenance Team, Red Hat**: `python-maint@redhat.com` [[.github/SECURITY.md:66-66]()]
- **Daniele Tricoli, Debian**: `@eriol` [[.github/SECURITY.md:67-67]()]

Sources: [.github/SECURITY.md:59-72]()

## Automated Security Analysis

The project utilizes automated tools to detect vulnerabilities during the development lifecycle.

### CodeQL Analysis
Requests employs GitHub's CodeQL analysis to scan for security vulnerabilities in the Python codebase. The workflow is configured to:
- Run on every push to the `main` branch [[.github/workflows/codeql-analysis.yml:9-10]()].
- Run on all pull requests targeting `main` [[.github/workflows/codeql-analysis.yml:11-13]()].
- Perform a weekly scheduled scan [[.github/workflows/codeql-analysis.yml:14-15]()].

The analysis uses the `github/codeql-action/init` action to initialize the environment for Python scanning [[.github/workflows/codeql-analysis.yml:48-51]()] and uploads results to the GitHub security-events dashboard [[.github/workflows/codeql-analysis.yml:25-25]()].

Sources: [.github/workflows/codeql-analysis.yml:1-74]()

## Diagrams

### Security Vulnerability Response Workflow

This diagram maps the natural language disclosure process to the GitHub security entities and communication channels.

```mermaid
flowchart TD
    Reporter["Security_Reporter"] -->|"Opens_draft_advisory"| GitHubSA["GitHub_Security_Advisory"]
    GitHubSA -->|"Creates_private_workspace"| PrivateRepo["Private_Vulnerability_Repo"]
    
    Maintainer["Requests_Maintainer"] -->|"Acknowledges_within_2_days"| GitHubSA
    Maintainer -->|"Develops_patch"| VulnFix["Vulnerability_Fix"]
    Maintainer -->|"Contacts"| Downstream["Downstream_Packagers"]
    
    VulnFix -->|"Release_on_Weekday"| SecurityRelease["Security_Release"]
    Downstream -->|"Prepare_packages"| DownstreamReleases["Downstream_Updates"]
    
    SecurityRelease -->|"Release_to"| PyPI["PyPI_Repository"]
    SecurityRelease -->|"Publish"| CVE["CVE_Identifier"]
    SecurityRelease -->|"Update"| Changelog["HISTORY_md"]
```

Sources: [.github/SECURITY.md:24-84]()

### Security Infrastructure and Scanning

This diagram associates security scanning configurations with the CI/CD pipeline entities.

```mermaid
flowchart LR
    subgraph "CI_Security_Entities"
        CodeQLWF[".github/workflows/codeql-analysis.yml"]
        SecurityPolicy[".github/SECURITY.md"]
    end

    subgraph "Actions_and_Steps"
        InitAction["github/codeql-action/init"]
        AnalyzeAction["github/codeql-action/analyze"]
        DraftAdvisory["github/psf/requests/security/advisories/new"]
    end

    CodeQLWF -->|"uses"| InitAction
    CodeQLWF -->|"uses"| AnalyzeAction
    SecurityPolicy -->|"points_to"| DraftAdvisory
    
    InitAction -->|"language"| Python["python"]
```

Sources: [.github/workflows/codeql-analysis.yml:48-74](), [.github/SECURITY.md:3-6]()

### Security Release Timeline

```mermaid
gantt
    title "Requests Security Release Process Timeline"
    dateFormat YYYY-MM-DD
    axisFormat %d
    
    section "Initial Response"
    "Vulnerability Report" :milestone, m1, 2024-01-01, 0d
    "Initial Acknowledgement (Max 2 days)" :after m1, 2d
    
    section "Assessment"
    "Reproduction & Confirmation" :2024-01-03, 3d
    
    section "Resolution"
    "Fix Development (Target 2 weeks)" :2024-01-06, 7d
    "Security Testing" :2024-01-13, 3d
    
    section "Release Coordination"
    "Downstream Notification" :milestone, m2, 2024-01-16, 0d
    "Packager Preparation (1 week)" :after m2, 7d
    "PyPI Release (Weekday)" :milestone, m3, 2024-01-23, 0d
```

Sources: [.github/SECURITY.md:31-57]()

---

# Page: Project Information

# Project Information

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [HISTORY.md](HISTORY.md)
- [MANIFEST.in](MANIFEST.in)
- [pyproject.toml](pyproject.toml)
- [src/requests/__version__.py](src/requests/__version__.py)

</details>



This page documents the project metadata, including version information, platform support, licensing, and packaging details. For detailed information about specific aspects, see [Dependencies](#8.1), [Versioning and Release History](#8.2), and [Package Structure](#8.3).

## Version Information

The Requests library version metadata is defined in `src/requests/__version__.py`. The project uses a semantic versioning scheme, and the `__version__` string is the primary source of truth for the current release.

### Current Version Metadata

| Attribute | Value |
|-----------|-------|
| `__title__` | `"requests"` |
| `__description__` | `"Python HTTP for Humans."` |
| `__version__` | `"2.34.2"` |
| `__build__` | `0x023402` |
| `__author__` | `"Kenneth Reitz"` |
| `__author_email__` | `"me@kennethreitz.org"` |
| `__license__` | `"Apache-2.0"` |
| `__copyright__` | `"Copyright Kenneth Reitz"` |
| `__url__` | `"https://requests.readthedocs.io"` |

The `__build__` attribute provides a hexadecimal representation of the version for programmatic comparison. Recent updates include the introduction of inline types in version 2.34.0 to replace external type stubs.

Sources: [src/requests/__version__.py:5-14](), [HISTORY.md:35-38](), [pyproject.toml:81]()

## License and Copyright

Requests is licensed under the Apache License 2.0. The project moved to this license to ensure compatibility with modern open-source distribution requirements and to provide clear patent grants.

| Property | Value |
|----------|-------|
| License | Apache-2.0 |
| Copyright | Copyright Kenneth Reitz |
| SPDX Identifier | Apache-2.0 |

Sources: [src/requests/__version__.py:12-13](), [pyproject.toml:9]()

## Python Version Support

The minimum Python version requirement is defined in `pyproject.toml`. As of version 2.33.0, Requests requires Python 3.10 or later. The project actively tracks upcoming Python releases, including experimental support for free-threading in Python 3.14.

### Current Python Version Compatibility

| Python Version | Support Status | Added | Dropped |
|----------------|---------------|-------|---------|
| Python 3.10    | Supported     | v2.27.0 | - |
| Python 3.11    | Supported     | v2.28.0 | - |
| Python 3.12    | Supported     | v2.32.0 | - |
| Python 3.13    | Supported     | v2.34.0 | - |
| Python 3.14    | Supported     | v2.32.5 | - |
| Python 3.15    | Supported     | v2.34.0 | - |
| PyPy 3.9+      | Supported     | v2.32.0 | - |
| Python 3.9     | **Dropped**   | - | v2.33.0 |
| Python 3.8     | **Dropped**   | - | v2.32.5 |
| Python 3.7     | **Dropped**   | - | v2.32.0 |

### Historical Python Support Changes

```mermaid
timeline
    title "Python Version Support Timeline"
    2022-06 : "v2.28.0" : "Dropped Python 2.7, 3.6" : "Added Python 3.11"
    2024-05 : "v2.32.0" : "Dropped Python 3.7" : "Added Python 3.12, PyPy 3.9/3.10"
    2025-08 : "v2.32.5" : "Dropped Python 3.8" : "Added Python 3.14"
    2026-03 : "v2.33.0" : "Dropped Python 3.9"
    2026-05 : "v2.34.0" : "Added Python 3.15, 3.14t"
```

Sources: [pyproject.toml:17](), [pyproject.toml:33-44](), [HISTORY.md:46-48](), [HISTORY.md:93](), [HISTORY.md:111-112](), [HISTORY.md:190-191]()

## Project Metadata

### Official Resources

| Resource | Location |
|----------|----------|
| Documentation | https://requests.readthedocs.io |
| Source Repository | https://github.com/psf/requests |
| PyPI Package | https://pypi.org/project/requests/ |

### Project Classification

The project is classified with the following trove classifiers in `pyproject.toml`:

- **Development Status**: 5 - Production/Stable
- **Intended Audience**: Developers
- **License**: OSI Approved :: Apache Software License
- **Operating System**: OS Independent
- **Programming Language**: Python :: 3 :: Only
- **Programming Language :: Python :: Free Threading**: 2 - Beta

Sources: [pyproject.toml:26-47](), [pyproject.toml:50-51]()

## Distribution and Packaging

### Package Contents

The Requests distribution includes the following files as specified in `MANIFEST.in`:

| File/Directory | Purpose |
|----------------|---------|
| `README.md` | Project documentation |
| `LICENSE` | Apache 2.0 license text |
| `NOTICE` | Copyright and attribution notices |
| `HISTORY.md` | Complete changelog |
| `requirements-dev.txt` | Development dependencies |
| `tests/*.py` | Test suite (recursive) |
| `tests/certs/*` | Test certificates for SSL testing |

### Build System

Requests uses a PEP 517 build system with `setuptools`.

- **Build Backend**: `setuptools.build_meta`
- **Configuration**: Declarative setup in `pyproject.toml`
- **Dynamic Versioning**: Version is pulled from `requests.__version__.__version__`
- **Package Location**: Source files are located in the `src` directory.

Sources: [pyproject.toml:1-3](), [pyproject.toml:80-84](), [MANIFEST.in:1-3](), [HISTORY.md:85]()

## Dependencies Overview

Requests relies on several core dependencies to handle low-level networking, security, and character encoding.

### Dependency Relationship Map

```mermaid
graph TB
    subgraph "RequestsPackage [src/requests]"
        Core["requests core"]
    end
    
    subgraph "ExternalDependencies"
        urllib3["urllib3 [>=1.26, <3]"]
        certifi["certifi [>=2023.5.7]"]
        idna["idna [>=2.5, <4]"]
        charset["charset_normalizer [>=2, <4]"]
    end
    
    Core --> urllib3
    Core --> certifi
    Core --> idna
    Core --> charset
```

### Core Dependencies Summary

| Dependency | Purpose | Requirement |
|------------|---------|-------------|
| `urllib3` | Connection pooling and HTTP protocol | `>=1.26, <3` |
| `certifi` | CA Bundle for SSL verification | `>=2023.5.7` |
| `idna` | Internationalized Domain Names in Applications | `>=2.5, <4` |
| `charset_normalizer` | Character encoding detection | `>=2, <4` |

For detailed information about dependency versions and optional extras (like `socks` or `chardet`), see the [Dependencies](#8.1) page.

Sources: [pyproject.toml:18-23](), [pyproject.toml:55-56]()

## Project Maintenance

The Requests project is maintained under the Python Software Foundation (PSF).

### Maintenance Team

| Name | Role |
|------|------|
| Kenneth Reitz | Author |
| Ian Stapleton Cordasco | Maintainer |
| Nate Prewitt | Maintainer |

### Code Structure to Entity Mapping

```mermaid
graph LR
    subgraph "NaturalLanguageSpace"
        Release["Release History"]
        Metadata["Package Metadata"]
        BuildSystem["Build System"]
        Versioning["Version String"]
    end

    subgraph "CodeEntitySpace"
        HistoryFile["HISTORY.md"]
        VersionFile["src/requests/__version__.py"]
        ProjectFile["pyproject.toml"]
        AttrVersion["requests.__version__.__version__"]
    end

    Release --- HistoryFile
    Metadata --- VersionFile
    BuildSystem --- ProjectFile
    Versioning --- AttrVersion
```

### Release Process

Requests follows a semantic versioning scheme. The release process involves updating the `HISTORY.md` file and the version metadata in `__version__.py`. For detailed information about the versioning strategy and release history, see the [Versioning and Release History](#8.2) page.

Sources: [pyproject.toml:10-16](), [pyproject.toml:80-81](), [src/requests/__version__.py:8-13]()

---

# Page: Dependencies

# Dependencies

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [pyproject.toml](pyproject.toml)
- [requirements-dev.txt](requirements-dev.txt)
- [setup.py](setup.py)
- [src/requests/compat.py](src/requests/compat.py)
- [src/requests/packages.py](src/requests/packages.py)
- [tests/test_help.py](tests/test_help.py)
- [tox.ini](tox.ini)

</details>



This document provides comprehensive information about the dependencies required by the Requests library, how they are managed, and their version requirements. Requests relies on several external libraries to handle low-level HTTP protocols, security, and character encoding.

## Core Dependencies Overview

Requests is designed to be a high-level interface. It delegates the heavy lifting of connection pooling and protocol implementation to `urllib3`, while using specialized libraries for SSL certificates, character detection, and domain name handling.

The following diagram maps the high-level system components to the specific code entities and external dependencies:

**Requests Dependency Mapping**
```mermaid
graph TD
    subgraph "Requests (Code Entity Space)"
        Session["requests.sessions.Session"]
        Adapter["requests.adapters.HTTPAdapter"]
        Compat["requests.compat"]
        Init["requests.__init__"]
        Packages["requests.packages"]
        Help["requests.help.info"]
    end

    subgraph "Mandatory External Dependencies"
        urllib3["urllib3"]
        certifi["certifi"]
        charset["charset_normalizer"]
        idna["idna"]
    end

    Session --> Adapter
    Adapter --> urllib3
    Init -- "check_compatibility()" --> urllib3
    Init -- "check_compatibility()" --> charset
    Compat -- "_resolve_char_detection()" --> charset
    Packages -- "__import__" --> urllib3
    Packages -- "__import__" --> idna
    Help -- "metadata" --> idna
    urllib3 --> certifi
    urllib3 --> idna
```

Sources: [src/requests/compat.py:38-54](), [pyproject.toml:18-23](), [src/requests/packages.py:8-15](), [tests/test_help.py:24-27]()

## Mandatory Dependencies

The core functionality of Requests requires the following packages. Version constraints are strictly enforced during installation and verified at runtime.

| Dependency | Version Constraint | Purpose |
|------------|-------------------|---------|
| `urllib3` | `>=1.26, <3` | Handles connection pooling and low-level HTTP logic. |
| `certifi` | `>=2023.5.7` | Provides a Root Certificate bundle for SSL/TLS verification. |
| `charset_normalizer` | `>=2, <4` | Detects character encoding in response bodies. |
| `idna` | `>=2.5, <4` | Support for Internationalized Domain Names (IDNA 2008). |

Sources: [pyproject.toml:18-23]()

### Compatibility Verification Logic

At runtime, Requests performs a version check to ensure that the installed versions of `urllib3` and character detection libraries are compatible. This is handled by the `check_compatibility` function within the package initialization.

**Compatibility Check Flow**
```mermaid
graph TD
    Start["requests.__init__"] --> CallCheck["check_compatibility()"]
    CallCheck --> VerifyUrllib3["Verify urllib3 >= 1.26, < 3"]
    VerifyUrllib3 --> DetectLib{"Which Charset Lib?"}
    DetectLib -- "chardet" --> CheckChardet["Verify 3.0.2 <= chardet < 8.0.0"]
    DetectLib -- "charset_normalizer" --> CheckNormalizer["Verify 2.0.0 <= charset_normalizer < 4.0.0"]
    CheckChardet --> End["Success"]
    CheckNormalizer --> End
    VerifyUrllib3 -- "Fail" --> Warn["Raise RequestsDependencyWarning"]
```

Sources: [pyproject.toml:18-23](), [src/requests/compat.py:22-29](), [src/requests/compat.py:38-54]()

## Optional Dependencies

Requests provides optional "extras" for specific use cases, such as SOCKS proxy support or alternative character detection.

| Extra Name | Dependency | Purpose |
|------------|------------|---------|
| `socks` | `PySocks>=1.5.6, !=1.5.7` | Enables support for SOCKS4/SOCKS5 proxies. |
| `use_chardet_on_py3` | `chardet>=3.0.2, <8` | Forces the use of `chardet` instead of `charset_normalizer`. |
| `security` | `[]` | Legacy extra for security enhancements. |

Sources: [pyproject.toml:53-56](), [tox.ini:14-18]()

### SOCKS Proxy Implementation
When the `socks` extra is installed, `urllib3` utilizes `PySocks` to create socket connections through a proxy. This is often used for Tor or internal corporate proxies. The `tox` environment `use_chardet_on_py3` explicitly tests this configuration.

Sources: [pyproject.toml:55](), [tox.ini:14-18]()

## Character Detection Resolution

Requests maintains a fallback mechanism for character detection. It prefers `charset_normalizer` but can use `chardet` if the former is missing or if the user explicitly requests it via optional dependencies.

The resolution logic in `src/requests/compat.py` works as follows:

1.  The function `_resolve_char_detection` iterates through a list of supported libraries: `("chardet", "charset_normalizer")`. [src/requests/compat.py:38-47]()
2.  It attempts to import each using `importlib.import_module`. [src/requests/compat.py:44]()
3.  The first successfully imported module is assigned to the `chardet` symbol used throughout the library for compatibility with legacy naming. [src/requests/compat.py:53]()

Sources: [src/requests/compat.py:36-52]()

## SSL and Cryptography

Requests automatically attempts to provide diagnostic information and verify SSL support through its utility functions.

- **System SSL Information**: The `requests.help.info()` function provides diagnostic data about the system's SSL version, which is verified in tests to ensure it is not empty. [tests/test_help.py:6-8]()
- **IDNA Support**: Requests verifies the availability of the `idna` package. If `idna` lacks a `__version__` attribute (common in very old versions), Requests handles it gracefully by returning an empty string rather than crashing. [tests/test_help.py:16-21]()

Sources: [tests/test_help.py:6-9](), [tests/test_help.py:16-27]()

## Internal Dependency Mapping (Legacy)

For historical reasons and backward compatibility, Requests maps external dependencies into a `requests.packages` namespace. This allows legacy code to access `urllib3` and `idna` as if they were submodules of Requests.

**Namespace Mapping Logic**
```mermaid
graph LR
    subgraph "Global sys.modules"
        U1["urllib3"]
        I1["idna"]
        C1["charset_normalizer/chardet"]
    end
    subgraph "requests.packages Namespace"
        U2["requests.packages.urllib3"]
        I2["requests.packages.idna"]
        C2["requests.packages.chardet"]
    end
    U1 -. "Alias" .-> U2
    I1 -. "Alias" .-> I2
    C1 -. "Alias" .-> C2
```

The mapping ensures that the identities are preserved, meaning `requests.packages.urllib3` is the same object as the global `urllib3`. This is achieved by iterating through `sys.modules` and aliasing any module starting with the package name to the `requests.packages` prefix. [src/requests/packages.py:8-15]()

Sources: [src/requests/packages.py:8-23]()

## Python Version Requirements

Requests requires **Python 3.10 or later**. This is strictly enforced during the build and execution process.

- **Enforcement**: `setup.py` checks `sys.version_info` and exits with an error if the version is below 3.10. [setup.py:3-5]()
- **Metadata**: `requires-python = ">=3.10"` is specified in the project configuration. [pyproject.toml:17]()
- **Supported Versions**: The library is tested against Python 3.10 through 3.14 (and includes placeholders for 3.15 and Free Threading builds). [pyproject.toml:35-44](), [tox.ini:2]()

Sources: [setup.py:3-5](), [pyproject.toml:17](), [pyproject.toml:35-44](), [tox.ini:1-2]()

---

# Page: Versioning and Release History

# Versioning and Release History

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.github/workflows/publish.yml](.github/workflows/publish.yml)
- [.github/workflows/typecheck.yml](.github/workflows/typecheck.yml)
- [.github/workflows/zizmor.yml](.github/workflows/zizmor.yml)
- [HISTORY.md](HISTORY.md)
- [MANIFEST.in](MANIFEST.in)
- [docs/community/release-process.rst](docs/community/release-process.rst)
- [src/requests/__version__.py](src/requests/__version__.py)

</details>



## Overview

The Requests library uses a semantic versioning scheme (MAJOR.MINOR.PATCH) to communicate API stability and changes. Version metadata is centralized in `src/requests/__version__.py` [[src/requests/__version__.py:1-15]](). The project maintains a rigorous release history in `HISTORY.md` [[HISTORY.md:1-2]](). Starting with version 2.33.0, the project migrated to a PEP 517 build system using `setuptools` [[HISTORY.md:84-85]]().

Sources: [src/requests/__version__.py:1-14](), [HISTORY.md:1-2](), [HISTORY.md:84-85]()

## Versioning Scheme

Requests follows strict semantic versioning rules established to manage user expectations and ensure stability across the ecosystem.

### Release Types

| Release Type | Version Format | Description |
| :--- | :--- | :--- |
| **Major** | `vX.0.0` | Includes breaking changes that disrupt backwards compatibility (e.g., changing an attribute to a method) [[docs/community/release-process.rst:9-18]](). |
| **Minor** | `vX.Y.0` | Includes new features and bug fixes; guaranteed to be backwards compatible within the same major version [[docs/community/release-process.rst:26-35]](). |
| **Hotfix** | `vX.Y.Z` | Strictly limited to bug fixes missed in the previous release. Does **not** include dependency upgrades [[docs/community/release-process.rst:37-45]](). |

### Version Metadata Implementation

The `src/requests/__version__.py` file serves as the single source of truth for versioning.

**Diagram: Version Metadata Distribution**
```mermaid
graph LR
    subgraph "Code Entity Space"
        V_FILE["src/requests/__version__.py"]
        V_STR["__version__ = '2.34.2'"]
        V_HEX["__build__ = 0x023402"]
    end

    subgraph "System Names"
        PYPI["PyPI Distribution"]
        DOCS["ReadTheDocs"]
        S_INIT["requests.__init__"]
    end

    V_FILE --> V_STR
    V_FILE --> V_HEX
    V_STR --> PYPI
    V_STR --> S_INIT
    V_STR --> DOCS
```

Sources: [docs/community/release-process.rst:9-45](), [src/requests/__version__.py:8-9]()

## Release Process

The release process is automated via GitHub Actions, ensuring reproducible builds and secure delivery to PyPI.

### Automation Workflow

The `publish.yml` workflow manages the lifecycle of a release from tag creation to distribution [[.github/workflows/publish.yml:1-6]]().

**Diagram: Release Automation Flow**
```mermaid
sequenceDiagram
    participant Git as "Git Tag (v*)"
    participant GHA as ".github/workflows/publish.yml"
    participant Build as "python -m build"
    participant PyPI as "PyPI (OIDC)"

    Git->>GHA: Push Tag Trigger
    GHA->>Build: Set SOURCE_DATE_EPOCH
    Build-->>GHA: Generate sdist & wheel
    GHA->>PyPI: Publish with Attestations
```

1.  **Trigger**: A push to a tag matching `v*` [[.github/workflows/publish.yml:4-6]]().
2.  **Build**: Uses `python -m build` to create source distributions and wheels [[.github/workflows/publish.yml:38-41]]().
3.  **Reproducibility**: Sets `SOURCE_DATE_EPOCH` from the last git commit timestamp to ensure bit-for-bit reproducible builds [[.github/workflows/publish.yml:40-41]]().
4.  **Verification**: Publishes to Test PyPI via `workflow_dispatch` if requested [[.github/workflows/publish.yml:74-96]]().
5.  **Publish**: Uses `pypa/gh-action-pypi-publish` with OpenID Connect (OIDC) attestations for secure PyPI uploads [[.github/workflows/publish.yml:69-73]]().

### Release Artifacts
The `MANIFEST.in` file defines which non-code files are included in the source distribution (`sdist`), including `README.md`, `LICENSE`, `NOTICE`, and `HISTORY.md` [[MANIFEST.in:1-4]]().

Sources: [.github/workflows/publish.yml:1-95](), [MANIFEST.in:1-3]()

## Python Version Compatibility

Requests periodically updates its supported Python versions to align with the upstream CPython lifecycle.

### Current Support Matrix (v2.34.2)

| Platform | Status | Version / Milestone |
| :--- | :--- | :--- |
| **Python 3.15** | ✓ Supported | Added support based on beta1 [[HISTORY.md:46-47]](). |
| **Python 3.14t** | ✓ Supported | Added support for free-threaded Python [[HISTORY.md:48]](). |
| **Python 3.12** | ✓ Supported | Officially added in 2.32.0 [[HISTORY.md:188]](). |
| **PyPy 3.11** | ✓ Supported | Added for Linux and macOS [[HISTORY.md:125]](). |
| **Python 3.9** | ✗ Dropped | Dropped in 2.33.0 following EOL [[HISTORY.md:93]](). |
| **Python 3.8** | ✗ Dropped | Dropped in 2.32.5 following EOL [[HISTORY.md:111]](). |

Sources: [HISTORY.md:46-48](), [HISTORY.md:93](), [HISTORY.md:111](), [HISTORY.md:125](), [HISTORY.md:188]()

## Security and Release History

The project uses hotfix and minor releases to address vulnerabilities identified via CVEs.

### Recent Security Milestones

*   **CVE-2026-25645 (v2.33.0)**: Updated `requests.utils.extract_zipped_paths` to use non-deterministic locations to prevent malicious file replacement [[HISTORY.md:79-82]]().
*   **CVE-2024-47081 (v2.32.4)**: Fixed an issue where malicious URLs could trick `netrc` into retrieving credentials for the wrong host [[HISTORY.md:117-119]]().
*   **CVE-2024-35195 (v2.32.0)**: Fixed a session-level vulnerability where `verify=False` on an initial request leaked into subsequent requests to the same origin [[HISTORY.md:162-166]]().

### Notable API Changes (v2.34.x)

*   **Inline Types**: v2.34.0 introduced native type hints, replacing external `typeshed` requirements [[HISTORY.md:34-38]](). This change is validated via `pyright` in CI [[.github/workflows/typecheck.yml:1-33]]().
*   **Input Type Widening**: v2.34.1 widened `json` input types to `Mapping` and `Sequence` [[HISTORY.md:21-22]]().
*   **Header Type Reversion**: v2.34.2 moved `headers` back to `Mapping` (from `MutableMapping`) to resolve variance issues with inferred dict types [[HISTORY.md:12-14]]().

### Feature Reversions
In version 2.32.5, the team reverted a global `SSLContext` caching feature originally introduced in 2.32.0 due to unsustainable maintenance issues and negative impacts on specific use cases [[HISTORY.md:104-107]]().

Sources: [HISTORY.md:12-14](), [HISTORY.md:21-22](), [HISTORY.md:34-38](), [HISTORY.md:79-82](), [HISTORY.md:104-107](), [HISTORY.md:117-119](), [HISTORY.md:162-166](), [.github/workflows/typecheck.yml:1-32]()

---

# Page: Package Structure

# Package Structure

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [HISTORY.md](HISTORY.md)
- [MANIFEST.in](MANIFEST.in)
- [docs/_static/requests-sidebar.png](docs/_static/requests-sidebar.png)
- [ext/requests-logo.ai](ext/requests-logo.ai)
- [ext/requests-logo.svg](ext/requests-logo.svg)
- [src/requests/__init__.py](src/requests/__init__.py)
- [src/requests/__version__.py](src/requests/__version__.py)
- [src/requests/packages.py](src/requests/packages.py)
- [src/requests/py.typed](src/requests/py.typed)
- [tests/test_packages.py](tests/test_packages.py)

</details>



This page documents the organization and structure of the Requests package codebase. It describes the directory layout, module organization, and the technical implementation of the distribution system.

## Repository Structure

The Requests library utilizes a modern Python project structure, employing the `src`-layout pattern to separate source code from configuration and tests.

```mermaid
graph TD
    Root["Requests Repository"] --> SrcDir["src/"]
    Root --> TestsDir["tests/"]
    Root --> ConfigFiles["Configuration Files"]
    Root --> ExtDir["ext/"]
    
    SrcDir --> RequestsPkg["requests/"]
    
    TestsDir --> UnitTests["*.py"]
    TestsDir --> TestCerts["certs/"]
    
    RequestsPkg --> PyTyped["py.typed"]
    RequestsPkg --> VersionFile["__version__.py"]
    
    ConfigFiles --> PyProject["pyproject.toml"]
    ConfigFiles --> Manifest["MANIFEST.in"]
    
    ExtDir --> Logos["requests-logo.ai/svg"]
```

Sources: [src/requests/py.typed:1-1](), [src/requests/__init__.py:1-10](), [MANIFEST.in:1-3](), [src/requests/__version__.py:1-14]()

## Source Layout and Module Organization

The core logic resides within `src/requests/`. The library is decomposed into functional modules that handle specific aspects of the HTTP lifecycle. The `__init__.py` file acts as the primary orchestrator, exporting the public API and performing critical environment validation.

```mermaid
graph TD
    subgraph "Core Logic"
        Models["models.py<br/>Request/Response Objects"]
        Sessions["sessions.py<br/>Session & Cookie Persistence"]
        API["api.py<br/>Functional Entry Points"]
    end

    subgraph "Support & Compatibility"
        Utils["utils.py<br/>Public Utilities"]
        Compat["compat.py<br/>Version Compatibility"]
        Packages["packages.py<br/>Dependency Redirects"]
        Init["__init__.py<br/>Package Exports & Logic"]
        Version["__version__.py<br/>Metadata"]
    end

    Init --> API
    Init --> Sessions
    Init --> Models
    Init --> Utils
    Init --> Packages
    Init --> Version
    API --> Sessions
    Sessions --> Models
```

Sources: [src/requests/__init__.py:158-186](), [src/requests/__init__.py:213-214](), [src/requests/compat.py:1-8](), [src/requests/packages.py:1-23]()

## Dependency Management and Compatibility

Requests maintains a unique approach to dependency management and environment compatibility through `requests.compat` and runtime checks in `__init__.py`.

| Module | Purpose |
|--------|---------|
| `compat.py` | Handles character detection library resolution (`chardet` vs `charset_normalizer`) and provides a unified interface for Python standard library imports like `json`, `urlparse`, and `cookielib`. [src/requests/compat.py:3-4]() |
| `__init__.py` | Performs runtime compatibility checks for `urllib3`, `chardet`, and `charset_normalizer` versions via `check_compatibility`, raising `RequestsDependencyWarning` if versions are unsupported. [src/requests/__init__.py:60-124]() |
| `packages.py` | Provides a redirection layer for internal dependencies like `urllib3`, `idna`, and `chardet` to ensure they can be accessed via the `requests.packages` namespace for backwards compatibility. [src/requests/packages.py:5-23]() |

### Environment Initialization
During package import, Requests performs several initialization steps:
1.  **Dependency Validation**: The `check_compatibility` function verifies that `urllib3` is at least version 1.21.1 and that character detection libraries meet version requirements. [src/requests/__init__.py:75-90]()
2.  **SNI Support**: If the standard library `ssl` module lacks SNI support, Requests attempts to inject `pyopenssl` into `urllib3`. [src/requests/__init__.py:135-139]()
3.  **Warning Suppression**: Silences `urllib3`'s `DependencyWarning` and configures `FileModeWarning` to default. [src/requests/__init__.py:150-152](), [src/requests/__init__.py:219-219]()
4.  **Logging**: The package initializes a `NullHandler` for the `requests` logger to prevent "No handler found" warnings. [src/requests/__init__.py:216-216]()

Sources: [src/requests/__init__.py:60-152](), [src/requests/packages.py:5-23](), [tests/test_packages.py:4-13]()

## Data Flow: From API to Transport

The following diagram bridges the functional API calls to the internal class entities that process them, highlighting the relationship between convenience functions and the underlying session management.

```mermaid
sequenceDiagram
    participant User as "User Code"
    participant API as "api.py (get, post, request)"
    participant Session as "sessions.Session"
    participant Request as "models.Request"
    participant Prepared as "models.PreparedRequest"
    participant Response as "models.Response"

    User->>API: requests.get(url)
    API->>Session: request('get', url, ...)
    Session->>Request: Request(method, url, ...)
    Request->>Prepared: prepare()
    Session->>Response: send(PreparedRequest)
    Response-->>User: returns Response
```

Sources: [src/requests/api.py:64-77](), [src/requests/__init__.py:171-185](), [src/requests/models.py:1-10]()

## Distribution and Build System

Requests transitioned to a PEP 517 build system using `setuptools` [HISTORY.md:85-85](). The distribution includes necessary documentation and license files via `MANIFEST.in`.

*   **Version Metadata**: Metadata is defined in `__version__.py` and imported into the main package. [src/requests/__version__.py:5-14](), [src/requests/__init__.py:159-170]()
*   **Distribution Manifest**: The `MANIFEST.in` ensures that `README.md`, `LICENSE`, `NOTICE`, `HISTORY.md`, and test certificates are included in source distributions (sdist). [MANIFEST.in:1-3](), [HISTORY.md:155-156]()
*   **Release History**: The `HISTORY.md` file tracks non-trivial changes, bugfixes, and security updates (e.g., CVE-2026-25645). [HISTORY.md:1-98]()

| Metadata Attribute | Source | Value Example |
|-------------------|--------|---------------|
| `__version__` | `__version__.py:8` | "2.34.2" |
| `__build__` | `__version__.py:9` | 0x023402 |
| `__cake__` | `__version__.py:14` | "✨ 🍰 ✨" |

Sources: [src/requests/__version__.py:5-14](), [MANIFEST.in:1-3](), [HISTORY.md:1-98]()

## Internal Type Safety

Requests 2.34.0 introduced comprehensive inline types, replacing external typeshed definitions [HISTORY.md:34-41]().

*   **Marker File**: `src/requests/py.typed` signals PEP 561 compliance. [src/requests/py.typed:1-1]()
*   **Type Refinement**: Recent versions refined types for `headers` (moving from `MutableMapping` back to `Mapping` to avoid invariance issues) and `json` inputs (widened to `Mapping` and `Sequence`). [HISTORY.md:12-24]()
*   **Public API**: Core classes like `Request`, `PreparedRequest`, and `Response` are exported in `__init__.py` for full type visibility. [src/requests/__init__.py:188-214]()

Sources: [src/requests/py.typed:1-1](), [HISTORY.md:34-41](), [src/requests/__init__.py:188-214]()

---

# Page: Glossary

# Glossary

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [AUTHORS.rst](AUTHORS.rst)
- [HISTORY.md](HISTORY.md)
- [MANIFEST.in](MANIFEST.in)
- [src/requests/__version__.py](src/requests/__version__.py)
- [src/requests/_internal_utils.py](src/requests/_internal_utils.py)
- [src/requests/_types.py](src/requests/_types.py)
- [src/requests/adapters.py](src/requests/adapters.py)
- [src/requests/auth.py](src/requests/auth.py)
- [src/requests/cookies.py](src/requests/cookies.py)
- [src/requests/exceptions.py](src/requests/exceptions.py)
- [src/requests/hooks.py](src/requests/hooks.py)
- [src/requests/models.py](src/requests/models.py)
- [src/requests/py.typed](src/requests/py.typed)
- [src/requests/sessions.py](src/requests/sessions.py)
- [src/requests/structures.py](src/requests/structures.py)
- [src/requests/utils.py](src/requests/utils.py)
- [tests/test_adapters.py](tests/test_adapters.py)
- [tests/test_requests.py](tests/test_requests.py)

</details>



This glossary defines codebase-specific terms, jargon, and domain concepts used throughout the Requests library. It is intended to assist onboarding engineers in navigating the internal architecture and data flow.

## Core Models and Data Structures

### PreparedRequest
The `PreparedRequest` is the internal representation of an HTTP request that is ready to be sent over the wire. Unlike the user-facing `Request` object, which contains high-level configuration, a `PreparedRequest` has resolved its URL, encoded its body, and finalized its headers [src/requests/models.py:311-311]().

*   **Implementation**: Defined in `src/requests/models.py`.
*   **Data Flow**: A `Request` is converted to a `PreparedRequest` via `Session.prepare_request()` [src/requests/sessions.py:481-481]() or `Request.prepare()` [src/requests/models.py:269-269]().

### CaseInsensitiveDict
A specialized dictionary-like object used primarily for HTTP headers. It allows for case-insensitive key lookups while preserving the case of the keys as they were first defined [src/requests/structures.py:14-14]().

*   **Implementation**: `src/requests/structures.py`.
*   **Usage**: Used for `Response.headers` [src/requests/models.py:724-724]() and `PreparedRequest.headers` [src/requests/models.py:321-321]().

### LookupDict
A dictionary subclass used for status code lookups. It allows accessing HTTP status codes by their name (e.g., `requests.codes.ok`) or their integer value [src/requests/structures.py:100-100]().

### RequestsCookieJar
A compatibility layer over the standard library `http.cookiejar.CookieJar`. It provides a more Pythonic dictionary-like interface for managing cookies while maintaining compatibility with `cookielib` [src/requests/cookies.py:318-318]().

### HookType
A type alias for callback functions that are triggered during the request/
