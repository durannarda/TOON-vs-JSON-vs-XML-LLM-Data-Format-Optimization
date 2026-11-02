# LLM Data Format Optimization: TOON vs JSON vs XML 🚀

This project is a research and testing environment that empirically compares JSON, XML, and TOON data formats to optimize **token budget**, **Time to First Token (TTFT)**, and **model response accuracy** when working with Large Language Models (LLMs).
## 📌 Project Overview
In today's token-based LLM ecosystem, the format in which data is provided to the model is critical for cost and performance. In this study:
- Traditional nested formats (**JSON** and **XML (minified)**) are compared against the **TOON** format, which is optimized for flat tabular data.
- Parser algorithms are built using **DFA (Deterministic Finite Automaton)** logic, strictly adhering to formal language theory.

## 🧠 Methodology and Theoretical Background

1. **Automata-Based Parser:** Since TOON's flat structure does not require a stack memory, it is parsed directly using a DFA. Nested structures like JSON and XML rely on Context-Free Grammars (CFG) and require Pushdown Automata (PDA).
2. **Realistic Token Estimation (BPE):** Token counts are calculated using the industry-standard OpenAI `tiktoken` library, rather than relying on simple string length estimations.
3. **Fair Comparison (Minification):** To offset XML's structural verbosity, XML data is minified (stripped of unnecessary whitespaces and line breaks) before testing.
4. **Bias-Preventing Query Set:** To prevent the model from answering purely from its pre-trained memory, tests are categorized into three distinct difficulty levels (**Schema, Lookup, and Aggregate**).

## ⚙️ Installation and Requirements

To run the project in your local environment, follow the steps below.

**Requirements:**
- Python 3.8+
- [Ollama](https://ollama.com/) (Recommended Model: `gemma3:1b`)
