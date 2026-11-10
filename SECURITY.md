# Security

APIK promises that a program that compiles never reaches undefined
behaviour in the C it generates. A way to break that promise, for example
generated C that overflows, reads out of bounds or divides by zero without
a check, is a security bug as well as a correctness bug.

## Reporting

Report it privately: on GitHub, open the repository's **Security** tab and
choose **Report a vulnerability**. Include the APIK program, `apik26
--version`, the C compiler and, if you have it, the UBSan report.

For a problem that cannot be exploited through a compiled program (a wrong
error message, a compiler crash), open an ordinary issue instead.

## Supported versions

Only the latest release gets fixes; see [`CHANGELOG.md`](CHANGELOG.md).
