import { expect, test } from "@playwright/test";

test("loads cardiac timeline, filters nodes, opens evidence, and completes upload simulation", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("合成演示数据，仅用于材料整理演示，不构成诊断或治疗建议。").first()).toBeVisible();
  await expect(page.getByRole("button", { name: /首次胸部不适就诊材料/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "2024-03-12" })).toBeVisible();
  await expect(page.getByRole("button", { name: "2025-01-16" })).toBeVisible();

  await page.getByRole("button", { name: "只看异常" }).click();
  await expect(page.getByRole("button", { name: /住院观察材料/ })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /转院前复诊材料/ })).toBeVisible();

  await page.getByLabel("按材料类型筛选").selectOption("出院小结");
  await expect(page.getByRole("button", { name: /出院小结材料/ })).toBeVisible();

  await page.getByRole("button", { name: /出院小结材料/ }).click();
  await page.locator(".evidence-item").filter({ hasText: "冠心病可能" }).click();
  await expect(page.getByRole("dialog", { name: "证据材料视图" })).toBeVisible();
  await expect(page.getByText("原图定位", { exact: true })).toBeVisible();
  await page.getByLabel("关闭证据视图").click();

  await page.getByRole("button", { name: "空结果演示" }).click();
  await expect(page.getByText("当前筛选下没有时间轴节点")).toBeVisible();

  await page.getByRole("button", { name: "模拟上传" }).click();
  await expect(page.getByText(/合成材料处理完成/)).toBeVisible();
});

test("shows low-confidence evidence in another synthetic case", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("选择演示病例").selectOption("demo-neuro-transfer-002");
  await expect(page.getByRole("button", { name: /头颅 MRI 报告材料/ })).toBeVisible();
  await page.getByRole("button", { name: /头颅 MRI 报告材料/ }).click();
  await expect(page.getByText("低置信度，待核验｜OCR 82%")).toBeVisible();
});
