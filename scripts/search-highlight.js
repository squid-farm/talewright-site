import { matchingTokens } from "./search-core.js";

export function highlightMatches(element, terms) {
  const document = element.ownerDocument;
  for (const mark of element.querySelectorAll("mark.search-match")) {
    mark.replaceWith(document.createTextNode(mark.textContent));
  }
  element.normalize();
  if (terms.length === 0) {
    return;
  }

  const walker = document.createTreeWalker(element, 4);
  const nodes = [];
  while (walker.nextNode()) {
    if (!walker.currentNode.parentElement.closest("nav, footer, script, style, .docs-source")) {
      nodes.push(walker.currentNode);
    }
  }
  for (const node of nodes) {
    const matches = matchingTokens(node.textContent, terms);
    if (matches.length === 0) {
      continue;
    }
    const fragment = document.createDocumentFragment();
    let offset = 0;
    for (const match of matches) {
      fragment.append(document.createTextNode(node.textContent.slice(offset, match.index)));
      const mark = document.createElement("mark");
      mark.className = "search-match";
      mark.textContent = match[0];
      fragment.append(mark);
      offset = match.index + match[0].length;
    }
    fragment.append(document.createTextNode(node.textContent.slice(offset)));
    node.replaceWith(fragment);
  }
}
