/*
Copyright The Kubernetes Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

// Code generated by client-gen. DO NOT EDIT.

package fake

import (
	"context"

	v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	labels "k8s.io/apimachinery/pkg/labels"
	schema "k8s.io/apimachinery/pkg/runtime/schema"
	types "k8s.io/apimachinery/pkg/types"
	watch "k8s.io/apimachinery/pkg/watch"
	testing "k8s.io/client-go/testing"
	v1alpha1 "sigs.k8s.io/scheduler-plugins/apis/scheduling/v1alpha1"
)

// FakeElasticQuotas implements ElasticQuotaInterface
type FakeElasticQuotas struct {
	Fake *FakeSchedulingV1alpha1
	ns   string
}

var elasticquotasResource = schema.GroupVersionResource{Group: "scheduling.x-k8s.io", Version: "v1alpha1", Resource: "elasticquotas"}

var elasticquotasKind = schema.GroupVersionKind{Group: "scheduling.x-k8s.io", Version: "v1alpha1", Kind: "ElasticQuota"}

// Get takes name of the elasticQuota, and returns the corresponding elasticQuota object, and an error if there is any.
func (c *FakeElasticQuotas) Get(ctx context.Context, name string, options v1.GetOptions) (result *v1alpha1.ElasticQuota, err error) {
	obj, err := c.Fake.
		Invokes(testing.NewGetAction(elasticquotasResource, c.ns, name), &v1alpha1.ElasticQuota{})

	if obj == nil {
		return nil, err
	}
	return obj.(*v1alpha1.ElasticQuota), err
}

// List takes label and field selectors, and returns the list of ElasticQuotas that match those selectors.
func (c *FakeElasticQuotas) List(ctx context.Context, opts v1.ListOptions) (result *v1alpha1.ElasticQuotaList, err error) {
	obj, err := c.Fake.
		Invokes(testing.NewListAction(elasticquotasResource, elasticquotasKind, c.ns, opts), &v1alpha1.ElasticQuotaList{})

	if obj == nil {
		return nil, err
	}

	label, _, _ := testing.ExtractFromListOptions(opts)
	if label == nil {
		label = labels.Everything()
	}
	list := &v1alpha1.ElasticQuotaList{ListMeta: obj.(*v1alpha1.ElasticQuotaList).ListMeta}
	for _, item := range obj.(*v1alpha1.ElasticQuotaList).Items {
		if label.Matches(labels.Set(item.Labels)) {
			list.Items = append(list.Items, item)
		}
	}
	return list, err
}

// Watch returns a watch.Interface that watches the requested elasticQuotas.
func (c *FakeElasticQuotas) Watch(ctx context.Context, opts v1.ListOptions) (watch.Interface, error) {
	return c.Fake.
		InvokesWatch(testing.NewWatchAction(elasticquotasResource, c.ns, opts))

}

// Create takes the representation of a elasticQuota and creates it.  Returns the server's representation of the elasticQuota, and an error, if there is any.
func (c *FakeElasticQuotas) Create(ctx context.Context, elasticQuota *v1alpha1.ElasticQuota, opts v1.CreateOptions) (result *v1alpha1.ElasticQuota, err error) {
	obj, err := c.Fake.
		Invokes(testing.NewCreateAction(elasticquotasResource, c.ns, elasticQuota), &v1alpha1.ElasticQuota{})

	if obj == nil {
		return nil, err
	}
	return obj.(*v1alpha1.ElasticQuota), err
}

// Update takes the representation of a elasticQuota and updates it. Returns the server's representation of the elasticQuota, and an error, if there is any.
func (c *FakeElasticQuotas) Update(ctx context.Context, elasticQuota *v1alpha1.ElasticQuota, opts v1.UpdateOptions) (result *v1alpha1.ElasticQuota, err error) {
	obj, err := c.Fake.
		Invokes(testing.NewUpdateAction(elasticquotasResource, c.ns, elasticQuota), &v1alpha1.ElasticQuota{})

	if obj == nil {
		return nil, err
	}
	return obj.(*v1alpha1.ElasticQuota), err
}

// UpdateStatus was generated because the type contains a Status member.
// Add a +genclient:noStatus comment above the type to avoid generating UpdateStatus().
func (c *FakeElasticQuotas) UpdateStatus(ctx context.Context, elasticQuota *v1alpha1.ElasticQuota, opts v1.UpdateOptions) (*v1alpha1.ElasticQuota, error) {
	obj, err := c.Fake.
		Invokes(testing.NewUpdateSubresourceAction(elasticquotasResource, "status", c.ns, elasticQuota), &v1alpha1.ElasticQuota{})

	if obj == nil {
		return nil, err
	}
	return obj.(*v1alpha1.ElasticQuota), err
}

// Delete takes name of the elasticQuota and deletes it. Returns an error if one occurs.
func (c *FakeElasticQuotas) Delete(ctx context.Context, name string, opts v1.DeleteOptions) error {
	_, err := c.Fake.
		Invokes(testing.NewDeleteActionWithOptions(elasticquotasResource, c.ns, name, opts), &v1alpha1.ElasticQuota{})

	return err
}

// DeleteCollection deletes a collection of objects.
func (c *FakeElasticQuotas) DeleteCollection(ctx context.Context, opts v1.DeleteOptions, listOpts v1.ListOptions) error {
	action := testing.NewDeleteCollectionAction(elasticquotasResource, c.ns, listOpts)

	_, err := c.Fake.Invokes(action, &v1alpha1.ElasticQuotaList{})
	return err
}

// Patch applies the patch and returns the patched elasticQuota.
func (c *FakeElasticQuotas) Patch(ctx context.Context, name string, pt types.PatchType, data []byte, opts v1.PatchOptions, subresources ...string) (result *v1alpha1.ElasticQuota, err error) {
	obj, err := c.Fake.
		Invokes(testing.NewPatchSubresourceAction(elasticquotasResource, c.ns, name, pt, data, subresources...), &v1alpha1.ElasticQuota{})

	if obj == nil {
		return nil, err
	}
	return obj.(*v1alpha1.ElasticQuota), err
}