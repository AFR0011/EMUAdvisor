# Publication Readiness

EMUAdvisor was developed in a university/research context. Before changing repository visibility to public, confirm that the author has the right to publish the source code and that no institutional, collaborator, or project agreement restricts redistribution.

## Release checklist

- [ ] Confirm source-code ownership and choose an appropriate license.
- [ ] Confirm that only publicly accessible EMU regulations are referenced or retrieved.
- [ ] Confirm generated crawl, index, audit, review, and conversation artifacts remain ignored.
- [ ] Confirm no secrets or real administrative credentials exist in the current tree or Git history.
- [ ] Run the required GitHub Actions core and browser-smoke jobs successfully.
- [ ] Human-review evaluation cases before describing any set as a gold benchmark.
- [ ] Keep the README disclaimer that this is independent research software, not an official EMU administrative service.

## Evaluation terminology

Several historical filenames contain the word `gold`. Those names are retained temporarily for compatibility with scripts and CI. They must not be interpreted as human-reviewed gold data. Until review is complete, public-facing documentation should refer to these as candidate/regression evaluation sets.

## Public-release principle

The public repository should demonstrate the retrieval, citation, refusal, evaluation, and local-generation architecture without implying institutional endorsement, production readiness, or stronger evaluation evidence than the repository currently supports.
