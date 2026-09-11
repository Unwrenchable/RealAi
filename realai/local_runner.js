const { Llama } = require("node-llama-cpp");

const model = new Qwen({
  modelPath: "C:\RealAI-clean\models\qwen2.5-coder-7b-instruct-q5_k_m.gguf",
  gpuLayers: 999
});

module.exports.run = async function(prompt) {
  const response = await model.createCompletion({
    prompt,
    maxTokens: 4096,
    temperature: 0.2
  });

  return response.text;
};
