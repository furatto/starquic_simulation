from pathlib import Path
import subprocess

def process_logs(path, output, server):
	tool = "../picoquic/build/picolog_t"

	files = list(path.glob("*.log"))

	for file in files:
		cid = file.stem.split(".")[0][:5]

		Path(f"{output}/{cid}/").mkdir(parents=True, exist_ok=True)

		csv_command  = f"{tool} -f csv {file}".split()
		qlog_command = f"{tool} -f qlog {file}".split()

		file = f"{output}/{cid}/{cid}.{'server' if server else 'client'}.csv"
		if not Path(file).is_file():
			with open(file, "w") as f:
				print("#", " ".join(csv_command))
				subprocess.run(csv_command, stdout = f)

		file = f"{output}/{cid}/{cid}.{'server' if server else 'client'}.qlog"
		if not Path(file).is_file():
			with open(file, "w") as f:
				print("#", " ".join(qlog_command))
				subprocess.run(qlog_command, stdout = f)

if __name__ == "__main__":
	server_logs = Path("../picoquic_leo/build/slogs")
	client_logs = Path("../picoquic/build/slogs")

	output = Path("processed_logs")

	process_logs(server_logs, output, server = True)
	
	if client_logs != server_logs:
		process_logs(client_logs, output, server = False)