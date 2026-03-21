# Lab setup

- [1. Required steps](#1-required-steps)
  - [1.1. Set up your fork](#11-set-up-your-fork)
    - [1.1.1. Fork the course instructors' repo](#111-fork-the-course-instructors-repo)
    - [1.1.2. Go to your fork](#112-go-to-your-fork)
    - [1.1.3. Enable issues](#113-enable-issues)
    - [1.1.4. Add a classmate as a collaborator](#114-add-a-classmate-as-a-collaborator)
    - [1.1.5. Protect your `main` branch](#115-protect-your-main-branch)
  - [1.2. Clone your fork and set up the environment](#12-clone-your-fork-and-set-up-the-environment)
  - [1.3. Stop Lab 6 services](#13-stop-lab-6-services)
  - [1.4. Start the services locally](#14-start-the-services-locally)
  - [1.5. Populate the database](#15-populate-the-database)
  - [1.6. Verify the local deployment](#16-verify-the-local-deployment)
  - [1.7. Deploy to your VM](#17-deploy-to-your-vm)
  - [1.8. Set up SSH for the autochecker](#18-set-up-ssh-for-the-autochecker)
  - [1.9. Set up LLM access (Qwen Code API)](#19-set-up-llm-access-qwen-code-api)
  - [1.10. Get a Telegram bot token](#110-get-a-telegram-bot-token)
  - [1.11. Coding agent](#111-coding-agent)

## 1. Required steps

> [!NOTE]
> This lab builds on the same tools and setup from previous labs.
> If you completed Labs 4–6, most tools are already installed.
> The main changes are: a new repo, cleaning up Lab 6, deploying, and getting a Telegram bot token.

> [!NOTE]
> This lab needs your university email and GitHub alias in the Autochecker bot <https://t.me/auchebot>. If you haven't registered, do so now. If you want to change something, contact your TA or try `/reset` in the autochecker bot.

> [!TIP]
> In the instructions below, values you need to replace are marked like this: **`YOUR_VALUE`**. Replace the entire placeholder (including the `<` and `>` if present) with your actual value.

> [!TIP]
> First ask your [coding agent](#111-coding-agent), then ask the TA.

### 1.1. Set up your fork

#### 1.1.1. Fork the course instructors' repo

1. Fork the [lab's repo](https://github.com/inno-se-toolkit/se-toolkit-lab-7).

We refer to your fork as `fork` and to the original repo as `upstream`.

#### 1.1.2. Go to your fork

1. Go to your fork: `https://github.com/`**`YOUR_GITHUB_USERNAME`**`/se-toolkit-lab-7`.

#### 1.1.3. Enable issues

1. [Enable issues](../../wiki/github.md#enable-issues).

#### 1.1.4. Add a classmate as a collaborator

1. [Add a collaborator](../../wiki/github.md#add-a-collaborator) — your partner.
2. Your partner should add you as a collaborator in their repo.

#### 1.1.5. Protect your `main` branch

1. [Protect a branch](../../wiki/github.md#protect-a-branch).

### 1.2. Clone your fork and set up the environment

1. Clone your fork to your local machine:

   ```terminal
   git clone https://github.com/YOUR_GITHUB_USERNAME/se-toolkit-lab-7
   ```

   Replace **`YOUR_GITHUB_USERNAME`** with your GitHub username.

2. Open the forked repo in `VS Code`.

3. Go to `VS Code Terminal`, [check that the current directory is `se-toolkit-lab-7`](../../wiki/shell.md#check-the-current-directory-is-directory-name), and install `Python` dependencies:

   ```terminal
   uv sync --dev
   ```

4. Create the environment file:

   ```terminal
   cp .env.docker.example .env.docker.secret
   ```

5. Configure the autochecker API credentials.

   The ETL pipeline fetches data from the autochecker dashboard API.
   Open `.env.docker.secret` and set:

   ```text
   AUTOCHECKER_API_LOGIN=YOUR_EMAIL@innopolis.university
   AUTOCHECKER_API_PASSWORD=YOUR_GITHUB_USERNAMEYOUR_TELEGRAM_ALIAS
   ```

   Replace **`YOUR_EMAIL`**, **`YOUR_GITHUB_USERNAME`**, and **`YOUR_TELEGRAM_ALIAS`** with your actual values. Example: if your GitHub username is `johndoe` and your Telegram alias is `jdoe`, the password is `johndoejdoe`.

   > [!IMPORTANT]
   > The credentials must match your autochecker bot registration.

6. Set `LMS_API_KEY` — this is the **backend API key** that protects your LMS endpoints (used for `Authorization: Bearer` in Swagger and the frontend). It is **not** the LLM key — that comes later.

   ```text
   LMS_API_KEY=set-it-to-something-and-remember-it
   ```

### 1.3. Stop Lab 6 services

> [!IMPORTANT]
> Labs 6 and 7 use the same ports (42001–42004). You **must** stop Lab 6 containers before starting Lab 7.

**Locally:**

```terminal
cd ../se-toolkit-lab-6
docker compose --env-file .env.docker.secret down
cd ../se-toolkit-lab-7
```

**On your VM** (do this now so you don't forget):

```terminal
ssh YOUR_VM_USERNAME@YOUR_VM_IP
cd ~/se-toolkit-lab-6
docker compose --env-file .env.docker.secret down
```

Replace **`YOUR_VM_USERNAME`** and **`YOUR_VM_IP`** with your values.

> [!NOTE]
> You must use `--env-file .env.docker.secret` — without it, `docker compose down` will fail because the compose file references required variables.

### 1.4. Start the services locally

1. (`Windows`/`macOS`) Make sure [Docker Desktop](../../wiki/docker.md#start-docker) is running.

2. Start the services in the background:

   ```terminal
   docker compose --env-file .env.docker.secret up --build -d
   ```

3. Check that the containers are running:

   ```terminal
   docker compose --env-file .env.docker.secret ps --format "table {{.Service}}\t{{.Status}}"
   ```

   You should see all four services running:

   ```terminal
   SERVICE    STATUS
   backend    Up 50 seconds
   caddy      Up 49 seconds
   pgadmin    Up 50 seconds
   postgres   Up 55 seconds (healthy)
   ```

> <h3>Troubleshooting</h3>
>
> **Port conflict (`port is already allocated`).**
>
> First, check what's using the port:
>
> ```terminal
> docker ps
> ```
>
> This shows all running containers and their ports. Look for containers using ports 42001–42004 — they're likely leftover from a previous lab. Stop them:
>
> ```terminal
> docker stop <container-name>
> ```
>
> If that doesn't help, make sure you stopped Lab 6 services (step 1.3), or [clean up `Docker`](../../wiki/docker.md#clean-up-docker) and try again.
>
> **Containers exit immediately.**
>
> Rebuild all containers from scratch:
>
> ```terminal
> docker compose --env-file .env.docker.secret down -v
> docker compose --env-file .env.docker.secret up --build -d
> ```
>
> **Hangs at `=> [caddy builder 4/7] RUN npm install -g pnpm`**
>
> or
>
> **DNS resolution errors (`getaddrinfo EAI_AGAIN`).**
>
> If you see DNS errors like `getaddrinfo EAI_AGAIN registry.npmjs.org`, `Docker` can't resolve domain names. This is a university network DNS issue. Add Google DNS to `Docker`:
>
> ```terminal
> sudo tee /etc/docker/daemon.json <<'EOF'
> {
>   "dns": ["8.8.8.8", "8.8.4.4"]
> }
> EOF
> sudo systemctl restart docker
> ```
>
> Then run the `docker compose up` command again.
>
> **Docker Hub rate limits (`Too many requests`).**
>
> If you're building outside the university network and hit Docker Hub rate limits, set the registry prefix to empty in `.env.docker.secret`:
>
> ```text
> REGISTRY_PREFIX=
> ```
>
> This is only needed outside the university. On campus, the default harbor cache avoids rate limits.

### 1.5. Populate the database

The database starts empty. You need to run the ETL pipeline to populate it with data from the autochecker API.

1. Open in a browser: `http://localhost:42002/docs`

   You should see the Swagger UI page.

2. [Authorize in Swagger](../../wiki/swagger.md#authorize-in-swagger-ui) with the `LMS_API_KEY` you set in `.env.docker.secret`.

3. Run the ETL sync by calling `POST /pipeline/sync` in Swagger UI.

   You should get a response showing the number of items and logs loaded:

   ```json
   {
     "new_records": 120,
     "total_records": 9502
   }
   ```

   > [!NOTE]
   > The exact numbers depend on how much data the autochecker API has.
   > As long as both numbers are greater than 0, the sync worked.

4. Verify data by calling `GET /items/`.

   You should get a non-empty array of items.

> [!IMPORTANT]
> Without this step, all analytics endpoints return empty results and your bot will have no data to work with.

### 1.6. Verify the local deployment

1. Open `http://localhost:42002/docs` in a browser.

   You should see the Swagger UI with all endpoints.

2. Open `http://localhost:42002/` in a browser.

   You should see the frontend. Enter your API key to connect.

3. Switch to the **Dashboard** tab.

   You should see charts with analytics data (submissions timeline, score distribution, group performance, task pass rates).

> [!IMPORTANT]
> If the dashboard shows no data or errors, make sure:
>
> - The ETL sync completed successfully (step 1.5)
> - You entered the correct API key in the frontend
> - Try selecting a different lab in the dropdown

### 1.7. Deploy to your VM

The autochecker tests your bot against your **deployed backend on your VM**. You need to deploy the same services there.

1. [Connect to the VM](../../wiki/vm-access.md#connect-to-the-vm-as-the-user-user-local).

2. Make sure Lab 6 is stopped (if you haven't done this in step 1.3):

   ```terminal
   cd ~/se-toolkit-lab-6 && docker compose --env-file .env.docker.secret down
   cd ~
   ```

3. Clone your fork on the VM:

   ```terminal
   git clone https://github.com/YOUR_GITHUB_USERNAME/se-toolkit-lab-7 ~/se-toolkit-lab-7
   ```

   Replace **`YOUR_GITHUB_USERNAME`** with your GitHub username.

4. Create the environment file:

   ```terminal
   cd ~/se-toolkit-lab-7
   cp .env.docker.example .env.docker.secret
   ```

5. Edit `.env.docker.secret` — set the same credentials as in your local file:

   ```terminal
   nano .env.docker.secret
   ```

   Set `AUTOCHECKER_API_LOGIN`, `AUTOCHECKER_API_PASSWORD`, and `LMS_API_KEY` (use the same values as locally).

6. Configure Docker DNS (required on most university VMs):

   ```terminal
   sudo tee /etc/docker/daemon.json <<'EOF'
   {
     "dns": ["8.8.8.8", "8.8.4.4"]
   }
   EOF
   sudo systemctl restart docker
   ```

   > [!NOTE]
   > Without this, Docker builds will fail with `getaddrinfo EAI_AGAIN` errors because the university network DNS can't resolve external registries like `registry.npmjs.org`.

7. Start the services:

   ```terminal
   docker compose --env-file .env.docker.secret up --build -d
   ```

   > <h3>Troubleshooting</h3>
   >
   > The same troubleshooting advice as when [starting the services locally](#14-start-the-services-locally).

8. Populate the database:

   ```terminal
   curl -X POST http://localhost:42002/pipeline/sync -H "Authorization: Bearer YOUR_LMS_API_KEY" -H "Content-Type: application/json" -d '{}'
   ```

   Replace **`YOUR_LMS_API_KEY`** with the value you set in `.env.docker.secret`.

9. Verify the deployment:

   ```terminal
   curl -s http://localhost:42002/items/ -H "Authorization: Bearer YOUR_LMS_API_KEY" | head -c 200
   ```

   You should see a JSON array of items.

> [!IMPORTANT]
> Keep the services running on your VM. The autochecker will query your backend during evaluation.

### 1.8. Set up SSH for the autochecker

The autochecker needs to SSH into your VM as **your main user** to run checks (test your bot, verify deployment, etc.).

> [!NOTE]
> If you completed Lab 6 Task 3, this is already done. Verify by checking with the autochecker bot — if the setup check passes, skip this step.

1. On your VM, add the autochecker's SSH public key:

   ```terminal
   mkdir -p ~/.ssh
   echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKiL0DDQZw7L0Uf1c9cNlREY7IS6ZkIbGVWNsClqGNCZ se-toolkit-autochecker' >> ~/.ssh/authorized_keys
   chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys
   ```

2. Register your VM username with the autochecker bot if you haven't already.

   In the Telegram bot, when prompted for your VM username, run `whoami` on your VM and reply with the output.

### 1.9. Set up LLM access (Qwen Code API)

Your bot needs an LLM for the intent routing feature (Task 3). [Qwen Code](../../wiki/qwen-code.md#what-is-qwen-code) provides **1000 free requests per day** and works from Russia — no VPN or credit card needed.

> [!NOTE]
> If you set up the Qwen Code API in Lab 6, it should still be running on your VM. Verify by running this **on your VM**:
>
> ```terminal
> grep QWEN_CODE_API_KEY ~/qwen-code-oai-proxy/.env
> ```
>
> This shows your key. Then test it:
>
> ```terminal
> curl -s http://localhost:42005/v1/models -H "Authorization: Bearer YOUR_QWEN_CODE_API_KEY" | head -c 100
> ```
>
> Replace **`YOUR_QWEN_CODE_API_KEY`** with the value from the grep output.
>
> If this returns a JSON response with model info, you're good — skip to the next step.

1. [Set up the Qwen Code API on your VM](../../wiki/qwen-code-api-deployment.md#deploy-the-qwen-code-api-remote).

   After completing the setup, you will have the Qwen API running on your VM at `http://localhost:42005/v1`.

<details><summary><b>Alternative: OpenRouter (click to open)</b></summary>

If you prefer [OpenRouter](https://openrouter.ai), register and get an API key. Then use:

```text
LLM_API_KEY=your-openrouter-key
LLM_API_BASE_URL=https://openrouter.ai/api/v1
LLM_API_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

</details>

### 1.10. Get a Telegram bot token

You need a Telegram bot token to run your bot client.

1. Open Telegram and search for [@BotFather](https://t.me/BotFather).

2. Send `/newbot`.

3. Choose a **name** for your bot (e.g., `My LMS Bot`).

4. Choose a **username** for your bot (must end in `bot`, e.g., `my_lms_lab7_bot`).

5. BotFather will reply with a token like:

   ```text
   123456789:ABCdefGhIJKlmNoPQRsTUVwxyz
   ```

6. Save this token.

7. Create the bot environment file on your VM:

   ```terminal
   cd ~/se-toolkit-lab-7
   cp .env.bot.example .env.bot.secret
   nano .env.bot.secret
   ```

   Fill in **all** fields:

   ```text
   BOT_TOKEN=your-token-from-botfather
   LMS_API_BASE_URL=http://localhost:42002
   LMS_API_KEY=same-value-as-in-env-docker-secret
   LLM_API_KEY=your-qwen-api-key-from-step-1.9
   LLM_API_BASE_URL=http://localhost:42005/v1
   LLM_API_MODEL=coder-model
   ```

   The `LMS_API_KEY` must match what you set in `.env.docker.secret`. The `LLM_API_KEY` is the `QWEN_CODE_API_KEY` from step 1.9.

8. Verify the LLM works from your VM:

   ```terminal
   curl -s http://localhost:42005/v1/chat/completions \
     -H "Authorization: Bearer YOUR_QWEN_CODE_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"coder-model","messages":[{"role":"user","content":"What is 2+2?"}]}' | head -c 100
   ```

   You should see a JSON response containing `"2 + 2 = 4"` or similar. If you get an error, fix the Qwen proxy setup (step 1.9) before continuing — the bot needs a working LLM for Task 3.

> [!IMPORTANT]
> Do not share your bot token or commit it to git. The file `.env.bot.secret` is already in `.gitignore` (any file matching `*.secret` is ignored).

### 1.11. Coding agent

> [!NOTE]
> You should already have a coding agent from previous labs.
> If not, [set one up](../../wiki/coding-agents.md#choose-and-use-a-coding-agent).

In this lab, you will use the coding agent (Qwen Code) extensively to plan, scaffold, and implement your Telegram bot. The agent is your development partner — learn to collaborate with it effectively.

----

You're all set. Now go to the [tasks](../../README.md#tasks).
