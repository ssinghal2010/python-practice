# Build Your Own Redis

A self-guided project to build a Redis-compatible server from scratch in Python. The goal is muscle memory in Python and genuine comfort with low-level networking, OS, and protocol work — not feature completeness.

---

## Why this project

This project hits everything you said you wanted:
- **Networking** — raw TCP sockets, not high-level HTTP libraries
- **OS-level concepts** — file descriptors, concurrency models, file I/O, persistence
- **Wire protocols** — designing and parsing a binary-ish format
- **Real Python** — sockets, threading or asyncio, bytes, file I/O, careful state management
- **Directly useful at Koraa** — Redis is everywhere in backend systems; understanding it changes how you read every cache and queue interaction

Why Redis specifically over Kafka or Shell:
- Simple enough protocol to bootstrap quickly
- Daily satisfying milestones (you'll see PONG come back on day 2)
- Testable with the real `redis-cli` — the moment a real client talks to your server, the project becomes real
- Better foundation for Kafka later — once you've done Redis, Kafka stops being "what is even happening" and becomes "more of the same with twists"

---

## The mental model

You're building a server that speaks a protocol. That's it. Strip away "Redis" and the project is:

1. A program that listens on a TCP port
2. Reads bytes from clients in a specific format
3. Does something with those bytes (store, retrieve, delete)
4. Writes bytes back in a specific format
5. Doesn't lose data when things go wrong

Every milestone below is just adding capability to one of those five things. When you feel lost, come back to this list — you're always working on one of them.

---

## The protocol: RESP

Redis clients and servers talk to each other using a text-based protocol called RESP (REdis Serialization Protocol). It's deliberately simple — that's why you can learn it in an afternoon.

**Read this first, before writing any code:**
https://redis.io/docs/latest/develop/reference/protocol-spec/

A few things you'll learn from it that you need before starting:
- Every message ends in `\r\n` (carriage return + line feed)
- The first byte tells you the type: `+` simple string, `-` error, `:` integer, `$` bulk string, `*` array
- Commands from clients always come as arrays of bulk strings. So `SET foo bar` arrives on the wire as:
  ```
  *3\r\n$3\r\nSET\r\n$3\r\nfoo\r\n$3\r\nbar\r\n
  ```
- Responses use the simpler types: `+OK\r\n`, `$3\r\nbar\r\n`, `:1\r\n`, etc.

Don't move on until that wire format clicks. Take a Redis command, decode it to bytes by hand on paper. This single hour will save you days of confusion later.

---

## Pre-flight checklist

Before you start writing code:

- [ ] Python 3.11+ installed and you know which `python` your terminal uses
- [ ] A clean folder with `git init` done
- [ ] `redis-cli` installed (`brew install redis` on Mac — you won't run the actual `redis-server`, just the CLI client)
- [ ] Two terminal windows (or a multiplexer) — server in one, `redis-cli` in the other
- [ ] A `notes.md` file in your project with today's date as the first line

---

## Where to start

Make a folder. Make a `server.py`. Don't overthink structure yet — single file is fine until it's painful, then you refactor. Premature folder structure is a procrastination trap.

## The milestones

### Milestone 1: TCP echo server

No Redis logic at all. Just:
- Listen on a port (use **6380** to avoid clashing with real Redis on 6379)
- Accept a connection
- Read whatever the client sends
- Send the same bytes back
- Close

Test it with `nc localhost 6380` (netcat) — type stuff, see it come back.

The Python stdlib `socket` module is what you need. Look up:
- `socket.socket`
- `bind`
- `listen`
- `accept`
- `recv`
- `sendall`

Ignore everything else for now.

**What you'll learn:** how TCP actually works at the syscall level, what a "connection" really is, why `recv` returns variable amounts of data, why network code is harder than it looks.

---

### Milestone 2: Respond to PING

Your server reads bytes, looks for the RESP-encoded `PING` command, and responds with `+PONG\r\n`.

The moment of magic: run `redis-cli -p 6380 PING` and your own server says PONG back. You've just spoken a real protocol to a real client.

Two hard things sneak in here that you must wrestle with yourself:

**Parsing.** You receive bytes. You need to turn `*1\r\n$4\r\nPING\r\n` into the concept "the client wants PING." Don't reach for a library. Write the parser. It's the whole point. Start ugly, refactor later.

**TCP gives you a stream, not messages.** `recv` might give you half a command, or two commands at once, or one and a half. This is the *framing problem*, and every network programmer hits it. You'll need a buffer that accumulates bytes and tries to parse complete commands from it.

Search terms when this confuses you: "tcp framing", "tcp message boundaries"

---

### Milestone 3: SET, GET, DEL with an in-memory dict

A Python dict at module level is your storage.

- `SET foo bar` → put `"foo": "bar"` in the dict, return `+OK\r\n`
- `GET foo` → return `$3\r\nbar\r\n`
- `GET missing` → return `$-1\r\n` (the RESP "null")
- `DEL foo` → return `:1\r\n` if it deleted something, `:0\r\n` if not

By now you have a thing that genuinely behaves like a tiny Redis. Use `redis-cli` for everything. Try weird stuff:
- `SET foo "hello world"` with spaces
- `GET` on something you never set
- Send malformed commands with `nc` and see what breaks

---

### Milestone 4: Handle multiple clients at once

Right now you can only serve one connection at a time — the next client has to wait.

Three approaches, in order of how much they'll teach you:

**1. One thread per connection** (`threading` module)
Easiest to wrap your head around. Has real problems (shared dict needs a lock) that teach you about concurrency hazards.

**2. `select`/`selectors` module**
The old-school single-threaded event loop. Painful and illuminating — this is what `asyncio` is built on top of, under the hood.

**3. `asyncio`**
Modern Python concurrency. If you go here, you're learning a whole paradigm (`async`/`await`, event loops, coroutines) on top of the networking stuff. Powerful but doubles your cognitive load.

**My honest take:** do `threading` first because you'll ship faster and learn about locks. If time permits, rewrite with `asyncio` later — the comparison is incredibly educational.

---

### Milestone 5: EXPIRE and TTL

- `SET foo bar EX 10` should store `foo` and delete it after 10 seconds
- `TTL foo` returns seconds remaining

This forces you to think about: where does the expiration check happen?
- **On read (lazy)** — check when someone tries to GET
- **In a background thread (active)** — periodically sweep
- Real Redis does both

You'll learn about `time.time()`, background tasks, and the trade-offs between approaches.

---

### Milestone 6: Persistence (AOF)

Right now your "database" dies when the server restarts.

Implement AOF (Append-Only File):
- Every write command, append the raw bytes to a file before responding OK
- On startup, read the file and replay every command
- Suddenly your server is durable across restarts

You'll learn file I/O, `fsync` (and why most people get durability wrong), and why "write to disk" is a lot more nuanced than it sounds.

---

### Stretch goals (if you have time)

- **RDB snapshots** — periodically dump the dict to a binary file
- **`INCR` and `INCRBY`** — atomicity matters here
- **`LPUSH` / `RPUSH` / `LRANGE`** — introduces a new data type (lists)
- **`INFO` command** — expose metrics about your server

---

## Things to read along the way, not upfront

Don't pre-read everything. Read when you hit the wall:

| When... | Search for... |
|---|---|
| Parsing breaks | "TCP stream framing", "delimiter-based vs length-prefixed protocols" |
| Concurrency confuses | "Python GIL", "threading.Lock", "race conditions" |
| Persistence feels off | "fsync write durability", "Redis AOF persistence" (the real docs) |
| Something is mysteriously slow | "Nagle's algorithm", "TCP_NODELAY" |
| You want depth | The actual Redis source code (in C, but readable). After you've written your own. |

---

## Ground rules for the 10 days

These exist because you specifically said you keep falling into the "re-read basics, never get comfortable" trap. Breaking them defeats the project's purpose.

1. **No AI writing your code.** Stack Overflow, docs, blog posts, the RESP spec, `man socket` — all fine. Me writing functions for you — not fine. Even pseudocode from me defeats the purpose.

2. **Get stuck for 30+ minutes before asking for help.** Stuckness is where the learning happens. If you bail at 5 minutes, you've optimized for completion, not comfort.

3. **Test with `redis-cli` constantly.** It's free, it's installed everywhere, and it'll tell you immediately when your server breaks the protocol.

4. **Commit to git after every working milestone.** Even just for you. Forces you to recognize progress.

5. **Keep a `notes.md` in the project.** When you Google something and learn it, write a sentence about it. By day 10 you'll have a personal reference doc that's worth more than any tutorial.

6. **When you're done — or stuck on something specific after real effort — paste code to me.** I'll review, point out non-idiomatic Python, flag bugs, suggest what to learn next. That's where I add value.

---

## Expectation-setting

10 days of focused work probably gets you through milestones 1-5 comfortably, and into milestone 6. Don't measure success by feature count — measure it by:

- Can you open a blank `.py` file and start a TCP server without looking things up?
- Do you reach for the right module instinctively (`socket`, `threading`, `time`)?
- When something breaks, do you know how to debug it (logging, `nc`, `redis-cli -v`)?
- Can you read the AOF file with `cat` and explain what's in it?

If yes to most of these by day 10 — Python isn't your bottleneck anymore. That's the whole point.

---

## After this project

When you finish (or hit day 10, whichever comes first):
- Push to GitHub with a real README explaining what it does and what it doesn't
- Bring the code to me for review — non-idiomatic Python, footguns, what would never survive a code review at Koraa
- Then decide: rewrite with `asyncio`? Build Kafka next? Jump to the RAG project? You'll be ready for any of them.

Now go build something that breaks.
