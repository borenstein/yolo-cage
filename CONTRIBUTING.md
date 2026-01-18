# Contributing

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

### Release Process

1. Create a PR with your changes
2. Add the appropriate version label (`major`, `minor`, or `patch`)
3. Get review and merge
4. GitHub Actions automatically:
   - Calculates the next version from the label
   - Creates a git tag
   - Creates a GitHub release with release notes
   - Attaches the `yolo-cage` script as a release artifact
