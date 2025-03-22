package routes

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"path"

	tea "github.com/charmbracelet/bubbletea"
	huh "github.com/charmbracelet/huh"
	"github.com/suban244/watson/watson-tui/config"
)

type AddTags struct {
	title         string
	form          *huh.Form
	availableTags []Tag
	error         error
}

func NewAddTagScreen() Screen {
	return AddTags{
		form: huh.NewForm(
			huh.NewGroup(
				huh.NewInput().Title("Tag Name").Prompt("> ").Key("tagName"),
				huh.NewInput().Title("Tag Description").Prompt("> ").Key("description"),
			),
		),
		title: "Add a new Tag",
	}
}

func (m AddTags) Init() tea.Cmd {
	var cmds []tea.Cmd

	cmds = append(cmds, getAllTags)
	cmds = append(cmds, m.form.Init())

	return tea.Batch(cmds...)
}

func (m AddTags) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmds []tea.Cmd

	form, cmd := m.form.Update(msg)
	if f, ok := form.(*huh.Form); ok {
		m.form = f
		cmds = append(cmds, cmd)
	}

	switch msg := msg.(type) {
	case getAllTagsFailedMsg:
		m.error = msg.Err
	case getAllTagsMsg:
		m.availableTags = append(m.availableTags, msg.Tags...)
	case createTagSuccessMsg:
		cmds = append(cmds, ReturnCmd())
	default:
		if m.form.State == huh.StateCompleted {
			name := m.form.GetString("tagName")
			description := m.form.GetString("description")
			tag := Tag{
				Name:        name,
				Description: description,
			}
			cmds = append(cmds, createCmdCreateTag(tag))
		}
	}

	return m, tea.Batch(cmds...)
}

func (m AddTags) View() string {
	content := fmt.Sprintf("%s\n\n", m.title)
	if m.error != nil {
		content += fmt.Sprintf("Error: %s", m.error)
	}
	switch m.form.State {
	case huh.StateCompleted:
		content += "Tag created successfully"
		return content
	default:
		content += m.form.View()
	}
	if len(m.availableTags) == 0 {
		return content
	}

	content += "\n\nAvailable Tags\n"
	for _, tag := range m.availableTags {
		content += fmt.Sprintf("%s: %s\n", tag.Name, tag.Description)
	}
	return content
}

type Tag struct {
	Id          string `json:"id"`
	Name        string `json:"name"`
	Description string `json:"description"`
}

type createTagSuccessMsg struct {
	Tag Tag
}

type getAllTagsMsg struct {
	Tags []Tag
}

type getAllTagsFailedMsg struct{ Err error }

func getAllTags() tea.Msg {
	var categoryList []Tag
	u, err := url.Parse(config.SERVER_URL)
	if err != nil {
		return getAllTagsFailedMsg{Err: err}
	}
	u.Path = path.Join(u.Path, "transaction", "tag", "list")

	client := &http.Client{}
	res, err := client.Get(u.String())
	if err != nil {
		return getAllTagsFailedMsg{Err: err}
	}

	defer res.Body.Close()

	if res.StatusCode != http.StatusOK {
		return getAllTagsFailedMsg{Err: fmt.Errorf("error fetching tags")}
	}
	body, err := io.ReadAll(res.Body)
	if err != nil {
		return getAllTagsFailedMsg{Err: err}
	}

	err = json.Unmarshal(
		body, &categoryList,
	)
	if err != nil {
		return getAllTagsFailedMsg{Err: err}
	}

	return getAllTagsMsg{Tags: categoryList}
}

type addANewTagFailedMsg struct {
	Err error
}

func createCmdCreateTag(tag Tag) tea.Cmd {
	return func() tea.Msg {
		u, err := url.Parse(config.SERVER_URL)
		if err != nil {
			return addANewTagFailedMsg{Err: err}
		}
		u.Path = path.Join(u.Path, "transaction", "tag")

		data, err := json.Marshal(tag)
		if err != nil {
			return addANewTagFailedMsg{Err: err}
		}

		client := &http.Client{}
		res, err := client.Post(u.String(), "application/json", bytes.NewBuffer(data))

		if err != nil {
			return addANewTagFailedMsg{Err: err}
		}

		defer res.Body.Close()
		body, err := io.ReadAll(res.Body)
		if err != nil {
			return addANewTagFailedMsg{Err: err}
		}

		if res.StatusCode != http.StatusOK {
			return addANewTagFailedMsg{Err: fmt.Errorf("error creating tag")}
		}

		var responseTag Tag
		err = json.Unmarshal(body, &tag)
		if err != nil {
			return addANewTagFailedMsg{Err: err}
		}
		return createTagSuccessMsg{Tag: responseTag}
	}
}
