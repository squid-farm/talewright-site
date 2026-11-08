import MiniSearch from "minisearch";

const TOKEN_PATTERN = /@[A-Z0-9_-]+|#[A-Z0-9_-]+|\{[A-Z0-9_:.-]+(?:#[A-Z0-9_-]+)?\}|->|[\p{L}\p{N}]+/giu;

export function tokenize(text) {
  return text.match(TOKEN_PATTERN)?.map((term) => term.toLocaleLowerCase("en-US")) ?? [];
}

export function createSearchIndex(records) {
  const index = new MiniSearch({
    fields: ["pageTitle", "heading", "body"],
    storeFields: ["pageTitle", "heading", "body", "url"],
    idField: "id",
    tokenize,
    processTerm: (term) => term.toLocaleLowerCase("en-US"),
  });
  index.addAll(records);
  return index;
}

export function searchRecords(index, query) {
  const normalizedQuery = query.trim();
  if (!normalizedQuery) {
    return [];
  }

  return index.search(normalizedQuery, {
    prefix: true,
    fuzzy: 0.2,
    boost: { pageTitle: 12, heading: 8, body: 1 },
  });
}

function isWithinEditDistance(left, right, limit) {
  if (Math.abs(left.length - right.length) > limit) {
    return false;
  }

  let previous = Array.from({ length: right.length + 1 }, (_, index) => index);
  for (let row = 1; row <= left.length; row += 1) {
    const current = [row];
    let minimum = row;
    for (let column = 1; column <= right.length; column += 1) {
      const cost = left[row - 1] === right[column - 1] ? 0 : 1;
      current[column] = Math.min(
        current[column - 1] + 1,
        previous[column] + 1,
        previous[column - 1] + cost,
      );
      minimum = Math.min(minimum, current[column]);
    }
    if (minimum > limit) {
      return false;
    }
    previous = current;
  }
  return previous[right.length] <= limit;
}

function matchingOffset(text, query) {
  for (const term of tokenize(query)) {
    const exactOffset = text.toLocaleLowerCase("en-US").indexOf(term);
    if (exactOffset >= 0) {
      return exactOffset;
    }
  }

  const queryTerms = tokenize(query).filter((term) => term.length >= 5);
  const words = /[\p{L}\p{N}]+/gu;
  for (const word of text.matchAll(words)) {
    const candidate = word[0].toLocaleLowerCase("en-US");
    for (const term of queryTerms) {
      const limit = Math.floor(term.length * 0.2);
      if (limit > 0 && isWithinEditDistance(candidate, term, limit)) {
        return word.index;
      }
    }
  }
  return 0;
}

export function createExcerpt(text, query, maxLength = 180) {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= maxLength) {
    return normalized;
  }

  const matchOffset = matchingOffset(normalized, query);
  let start = Math.max(0, matchOffset - Math.floor(maxLength / 4));
  if (start > 0) {
    const nextSpace = normalized.indexOf(" ", start);
    start = nextSpace < 0 ? start : nextSpace + 1;
  }

  let end = Math.min(normalized.length, start + maxLength);
  if (end < normalized.length) {
    const previousSpace = normalized.lastIndexOf(" ", end);
    if (previousSpace > start) {
      end = previousSpace;
    }
  }

  return `${start > 0 ? "... " : ""}${normalized.slice(start, end).trim()}${end < normalized.length ? " ..." : ""}`;
}
