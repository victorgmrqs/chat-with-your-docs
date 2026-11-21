# When to Mock

**Never mock the database.** Backend tests run against a real PostgreSQL (the project's test database), so queries, constraints and migrations are exercised for real. Mocking a repository or session hides exactly the bugs that matter.

Use **at most 3 mocks per test**. More than that means the test is wired to implementation details or the unit is too big: move the seam.

Mock at **system boundaries** only. In this project the mocked boundaries are:

- **LLM and embedding providers**: replace them with declared fakes (small hand-written classes implementing the port, returning deterministic output), not ad-hoc `patch` calls scattered through tests
- **Time/randomness**: inject a clock or freeze time
- **External HTTP**: on the frontend, intercept with MSW at the network layer (never `vi.stubGlobal('fetch', ...)`); on the backend, fake the outbound client behind its port

Don't mock:

- The database (real PostgreSQL)
- Your own classes/modules
- Internal collaborators
- Anything you control

```python
# GOOD (pytest): real DB via fixture, declared fake for the LLM provider, frozen time
class FakeLLM:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.prompts: list[str] = []

    async def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answer

async def test_answer_uses_retrieved_chunks(db_session, frozen_clock):
    llm = FakeLLM("42")  # 1 fake + frozen clock = well under the 3-mock budget
    use_case = AnswerQuestion(chunks=PgChunkRepository(db_session), llm=llm, clock=frozen_clock)
    result = await use_case.execute("What is the answer?")
    assert result.text == "42"
```

```typescript
// GOOD (Vitest): HTTP boundary mocked with MSW, component rendered for real
server.use(http.post("/api/chat", () => HttpResponse.json({ answer: "42" })));
render(<Chat />);
await userEvent.type(screen.getByRole("textbox"), "What is the answer?");
await userEvent.click(screen.getByRole("button", { name: /send/i }));
expect(await screen.findByText("42")).toBeInTheDocument();
```

## Designing for Mockability

At system boundaries, design interfaces that are easy to mock:

**1. Use dependency injection**

Pass external dependencies in rather than creating them internally:

```typescript
// Easy to mock
function processPayment(order, paymentClient) {
  return paymentClient.charge(order.total);
}

// Hard to mock
function processPayment(order) {
  const client = new StripeClient(process.env.STRIPE_KEY);
  return client.charge(order.total);
}
```

```python
# Easy to fake: the provider is a constructor argument (wired in the composition root)
class Ingest:
    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder

# Hard to fake: provider created inside the function
async def ingest(text: str) -> None:
    embedder = OpenAIEmbedder(api_key=os.environ["OPENAI_API_KEY"])
```

**2. Prefer SDK-style interfaces over generic fetchers**

Create specific functions for each external operation instead of one generic function with conditional logic:

```typescript
// GOOD: Each function is independently mockable
const api = {
  getUser: (id) => fetch(`/users/${id}`),
  getOrders: (userId) => fetch(`/users/${userId}/orders`),
  createOrder: (data) => fetch('/orders', { method: 'POST', body: data }),
};

// BAD: Mocking requires conditional logic inside the mock
const api = {
  fetch: (endpoint, options) => fetch(endpoint, options),
};
```

The SDK approach means:
- Each mock returns one specific shape
- No conditional logic in test setup
- Easier to see which endpoints a test exercises
- Type safety per endpoint
