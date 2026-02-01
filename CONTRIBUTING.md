# Contributing

## Code Contributions

When contributing code or documentation:
- Use the [ubiquitous language](docs/glossary.md) defined in the glossary
- Follow existing code patterns and type hints
- Update relevant documentation

## Pull Requests

PRs merged to `main` automatically create a new release.

### Version Bumps

Add a label to your PR to control the version bump:

| Label | When to use | Example |
|-------|-------------|---------|
| `major` | Breaking changes | Removing a command, changing config format |
| `minor` | New features | Adding a new command, new config option |
| `patch` | Bug fixes, docs (default) | Fixing a bug, updating docs |

If no label is specified, `patch` is assumed.

### Alpha Versioning (0.x.x)

While yolo-cage is in alpha, semantic versioning is demoted by one level:

- **Breaking changes** → `minor` (not `major`)
- **Everything else** → `patch`
- **No `major` bumps** until we're ready for 1.0

This signals that the API is unstable and users should expect breaking changes in minor releases.

### Release Process

1. Create a PR with your changes
2. Add the appropriate version label (`major`, `minor`, or `patch`)
3. Get review and merge
4. GitHub Actions automatically:
   - Calculates the next version from the label
   - Creates a git tag
   - Creates a GitHub release with release notes
   - Attaches the `yolo-cage` script as a release artifact
