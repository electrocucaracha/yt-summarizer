# Copilot Instructions

## Purpose

This document provides guidelines for integrating GitHub Copilot into the `yt-summarizer` project.
It outlines best practices for leveraging Copilot to enhance productivity and maintain code quality.

## Best Practices

1. **Code Clarity**:
   - Write clear and concise comments to help Copilot understand the context.
   - Use descriptive variable and function names.

2. **Iterative Development**:
   - Use Copilot suggestions as a starting point and refine the code iteratively.
   - Validate the generated code against project requirements.

3. **Testing**:
   - Ensure all Copilot-generated code is covered by unit tests.
   - Use `pytest` to validate functionality and catch potential issues.

4. **Documentation**:
   - Document all Copilot-generated code to ensure maintainability.
   - Follow the project's documentation standards as outlined in the [CONTRIBUTING.md](../CONTRIBUTING.md) file.
   - Use semantic line breaks for Markdown prose, following [SEMBR](https://sembr.org/).
   - Preserve the structure of code fences, tables, YAML front matter, and concise list items unless a wrapped continuation clearly improves readability.

5. **Security**:
   - Review Copilot suggestions for potential security vulnerabilities.
   - Avoid using sensitive data in prompts.

## Integration Steps

1. **Setup**:
   - Install the GitHub Copilot extension in your IDE.
   - Authenticate with your GitHub account.

2. **Configuration**:
   - Enable Copilot for the `yt-summarizer` project.
   - Adjust settings to align with project-specific needs.

3. **Usage**:
   - Use Copilot to generate boilerplate code, suggest improvements, and explore alternative implementations.

4. **Feedback**:
   - Provide feedback on Copilot suggestions to improve its accuracy over time.

## Additional Resources

- [Project Contribution Guidelines](../CONTRIBUTING.md)

---

By following these guidelines, developers can effectively integrate GitHub Copilot into the `yt-summarizer` project,
enhancing productivity and maintaining high code quality.
