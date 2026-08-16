const messagesEl = document.getElementById("messages");

function scrollDown() { messagesEl.scrollTop = messagesEl.scrollHeight; }
function isNearBottom() {
  return messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight < 60;
}

const EXAMPLES = [
  "Which model should I use for ZDHHC20 in PDAC for target validation?",
  "Does the pancreatic line MIA PaCa-2 carry a KRAS mutation?",
  "Recommend a model for KRAS in colorectal cancer for an HTS screen",
];

function renderEmptyState() {
  const wrap = el("div", "empty");
  wrap.id = "empty";
  const mark = el("div", "empty__mark");
  mark.innerHTML = document.querySelector(".mark svg").outerHTML;
  wrap.appendChild(mark);
  wrap.appendChild(el("div", "empty__title", "Cellar"));
  wrap.appendChild(el("div", "empty__sub", "Find the right model to test your hypothesis"));
  wrap.appendChild(el("div", "empty__hint", "Try asking"));
  const prompts = el("div", "empty__prompts");
  EXAMPLES.forEach((p) => {
    const b = el("button", "example", p);
    b.type = "button";
    b.addEventListener("click", () => send(p));
    prompts.appendChild(b);
  });
  wrap.appendChild(prompts);
  messagesEl.appendChild(wrap);
}

function clearEmptyState() {
  const e = document.getElementById("empty");
  if (e) e.remove();
}

function addUser(text) {
  const wrap = el("div", "user");
  wrap.appendChild(el("div", "eyebrow", "you"));
  wrap.appendChild(el("div", "bubble", text));
  messagesEl.appendChild(wrap);
}

function addAssistant() {
  const wrap = el("div", "assistant");
  wrap.appendChild(el("div", "eyebrow", "Cellar"));
  const body = el("div", "body");
  const caret = el("span", "caret");
  body.appendChild(caret);
  wrap.appendChild(body);
  messagesEl.appendChild(wrap);
  return { body, caret, cursorText: null };
}

function appendText(a, t) {
  if (!a.cursorText) {
    a.cursorText = el("div", "text md");
    a.cursorText._raw = "";
    a.body.insertBefore(a.cursorText, a.caret);
  }
  a.cursorText._raw += t;
  a.cursorText.innerHTML = renderMarkdown(a.cursorText._raw);
}
