import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getConfig, updateConfig } from "../api";

function parseFrontmatter(md: string) {
  const match = md.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!match) return { name: "", description: "", body: md };
  const fm = match[1];
  const body = match[2].trim();
  const name = (fm.match(/^name:\s*(.+)$/m) ?? [])[1]?.trim() ?? "";
  const description = (fm.match(/^description:\s*(.+)$/m) ?? [])[1]?.trim() ?? "";
  return { name, description, body };
}

function buildFrontmatter(name: string, description: string, body: string) {
  return `---\nname: ${name}\ndescription: ${description}\n---\n\n${body}`;
}

export default function Skills() {
  const qc = useQueryClient();
  const { data: config } = useQuery({ queryKey: ["config"], queryFn: getConfig });
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [body, setBody] = useState("");

  useEffect(() => {
    if (config) {
      const p = parseFrontmatter(config.skill_md);
      setName(p.name);
      setDescription(p.description);
      setBody(p.body);
    }
  }, [config]);

  const mutation = useMutation({
    mutationFn: () => updateConfig({ skill_md: buildFrontmatter(name, description, body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["config"] }),
  });

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Skills</h1>
      <p className="text-sm text-gray-500">The SKILL.md that tells the agent how to build the PDF.</p>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)}
            placeholder="digest-pdf"
            className="w-full border rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Description</label>
          <input value={description} onChange={(e) => setDescription(e.target.value)}
            placeholder="Convert a tech news digest into a clean PDF."
            className="w-full border rounded-lg px-3 py-2 text-sm" />
        </div>
      </div>
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={14}
        placeholder="# Digest PDF Skill&#10;&#10;When the user asks for a PDF, follow this exact procedure:&#10;&#10;1. If reportlab isn't installed, run `pip install reportlab`.&#10;2. Build the PDF at /workspace/digest.pdf using ReportLab."
        className="w-full border rounded-lg px-3 py-2 text-sm font-mono resize-y"
      />
      <div className="flex justify-end">
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
        >
          {mutation.isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </div>
  );
}
