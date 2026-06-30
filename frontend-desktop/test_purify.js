const jsdom = require("jsdom");
const { JSDOM } = jsdom;
const window = new JSDOM("").window;
const DOMPurify = require("dompurify")(window);

const rawHtml = '<img src="media://d:/My Self Details/Programs/AI/msa_agent/data/memory/user_picture.jpg" />';
const sanitized = DOMPurify.sanitize(rawHtml, {
  ADD_TAGS: ['pre', 'code', 'button'],
  ADD_ATTR: ['onclick', 'class', 'style'],
  ALLOW_DATA_ATTR: false,
  ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto|tel|data|media):|[^&:\/?#]*(?:[\/?#]|$))/i,
});

console.log("Sanitized HTML:", sanitized);
