#!/usr/bin/env python3
"""Format GitHub PR inline comments as Markdown.

Uses GitHub GraphQL API to fetch review threads with resolved status.

Usage with gh CLI:
    ./format_pr.py [PR_NUMBER]

If PR_NUMBER is not provided, uses the current PR from the branch.
"""

import json
import subprocess
import sys


def run_gh_command(args):
    """Run a gh CLI command and return the output."""
    result = subprocess.run(
        ['gh'] + args,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout


def get_repo_info():
    """Get the owner and repo name from the current git repository."""
    # Get remote URL
    result = subprocess.run(
        ['git', 'config', '--get', 'remote.origin.url'],
        capture_output=True,
        text=True,
        check=True
    )
    url = result.stdout.strip()

    # Parse owner/repo from URL (handles both HTTPS and SSH)
    # Example: git@github.com:owner/repo.git or https://github.com/owner/repo.git
    if 'github.com' in url:
        parts = url.split('github.com')[-1].strip(':/')
        parts = parts.replace('.git', '')
        owner, repo = parts.split('/')[:2]
        return owner, repo

    raise ValueError(f"Could not parse GitHub repo from URL: {url}")


def get_pr_number():
    """Get the PR number for the current branch.

    Returns None if no PR exists for the current branch.
    """
    try:
        output = run_gh_command(['pr', 'view', '--json', 'number', '-q', '.number'])
        return int(output.strip())
    except subprocess.CalledProcessError:
        return None


def fetch_review_threads(owner, repo, pr_number):
    """Fetch review threads using GitHub GraphQL API."""
    query = """
    query($owner: String!, $repo: String!, $pr: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $pr) {
          reviewThreads(first: 100) {
            nodes {
              isResolved
              isOutdated
              comments(first: 100) {
                nodes {
                  id
                  author {
                    login
                  }
                  body
                  path
                  line
                  diffHunk
                  url
                }
              }
            }
          }
        }
      }
    }
    """

    # Use gh api graphql command
    output = run_gh_command([
        'api', 'graphql',
        '-f', f'query={query}',
        '-F', f'owner={owner}',
        '-F', f'repo={repo}',
        '-F', f'pr={pr_number}'
    ])

    return json.loads(output)


def format_threads(data):
    """Format review threads as Markdown."""
    threads = data['data']['repository']['pullRequest']['reviewThreads']['nodes']

    # Count resolved vs unresolved
    resolved_count = sum(1 for t in threads if t['isResolved'])
    unresolved_count = len(threads) - resolved_count

    print(f"# PR Review Comments ({len(threads)} threads)\n")
    print(f"- **Unresolved:** {unresolved_count}")
    print(f"- **Resolved:** {resolved_count}\n")

    # Group by resolved status
    unresolved_threads = [t for t in threads if not t['isResolved']]
    resolved_threads = [t for t in threads if t['isResolved']]

    # Show unresolved first
    if unresolved_threads:
        print("## Unresolved Comments\n")
        for thread in unresolved_threads:
            format_thread(thread, resolved=False)

    if resolved_threads:
        print("## Resolved Comments\n")
        for thread in resolved_threads:
            format_thread(thread, resolved=True)


def format_thread(thread, resolved):
    """Format a single review thread."""
    comments = thread['comments']['nodes']
    if not comments:
        return

    # First comment is the main one
    first_comment = comments[0]
    author = first_comment['author']['login'] if first_comment['author'] else 'Unknown'
    path = first_comment.get('path', 'unknown file')
    line = first_comment.get('line', '?')
    body = first_comment.get('body', '')
    diff_hunk = first_comment.get('diffHunk', '')
    url = first_comment.get('url', '')

    status = "✅ RESOLVED" if resolved else "⚠️  UNRESOLVED"
    if thread.get('isOutdated'):
        status += " (outdated)"

    print(f"### [{status}] {author} on `{path}:{line}`\n")

    if url:
        print(f"[View on GitHub]({url})\n")

    # Include the code diff context if available
    if diff_hunk:
        print(f"```diff\n{diff_hunk}\n```\n")

    print(f"{body}\n")

    # Show replies if any
    if len(comments) > 1:
        print("**Replies:**\n")
        for reply in comments[1:]:
            reply_author = reply['author']['login'] if reply['author'] else 'Unknown'
            reply_body = reply.get('body', '')
            print(f"- **{reply_author}:** {reply_body}")
        print()

    print("---\n")


def main():
    try:
        # Get PR number from argument or current branch
        if len(sys.argv) > 1:
            pr_number = int(sys.argv[1])
        else:
            pr_number = get_pr_number()
            if pr_number is None:
                # Get current branch name for the message
                result = subprocess.run(
                    ['git', 'branch', '--show-current'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                branch = result.stdout.strip()
                print(f"No pull request found for branch '{branch}'", file=sys.stderr)
                print("\nTo view comments for a specific PR, "+
                      "use: make pr-comments PR=<number>", file=sys.stderr)
                print("Or run: python3 .opencode/skills/pr/bin/format_pr.py <PR_NUMBER>", file=sys.stderr)
                sys.exit(0)  # Exit cleanly, not an error condition

        # Get repo info
        owner, repo = get_repo_info()

        # Fetch and format review threads
        data = fetch_review_threads(owner, repo, pr_number)
        format_threads(data)

    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}", file=sys.stderr)
        print(f"Output: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
